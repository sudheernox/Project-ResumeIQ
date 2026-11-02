"""
Resume Analyzer — computes quality scores from parsed resume text
"""
import re
import json
from typing import List, Dict, Any


# ─── Skill Dictionaries ────────────────────────────────────────────────────────

TECHNICAL_SKILLS = {
    # Languages
    'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', 'go', 'rust',
    'swift', 'kotlin', 'ruby', 'php', 'scala', 'r', 'matlab', 'perl', 'bash', 'shell',
    'dart', 'lua', 'haskell', 'elixir', 'clojure',
    # Web
    'html', 'css', 'html5', 'css3', 'react', 'reactjs', 'angular', 'angularjs',
    'vue', 'vuejs', 'next.js', 'nextjs', 'node.js', 'nodejs', 'express', 'expressjs',
    'django', 'flask', 'fastapi', 'spring', 'springboot', 'laravel', 'rails',
    'bootstrap', 'tailwind', 'sass', 'less', 'jquery', 'redux',
    'graphql', 'rest', 'restful', 'api', 'websocket',
    # Data / AI
    'machine learning', 'deep learning', 'neural network', 'nlp',
    'natural language processing', 'computer vision', 'tensorflow', 'pytorch',
    'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'matplotlib',
    'seaborn', 'plotly', 'opencv', 'huggingface', 'transformers',
    'data science', 'data analysis', 'data visualization', 'statistics',
    'big data', 'hadoop', 'spark', 'pyspark', 'kafka', 'airflow',
    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'dynamodb', 'oracle', 'mssql', 'nosql', 'elasticsearch', 'firebase',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s',
    'terraform', 'ansible', 'jenkins', 'github actions', 'ci/cd', 'devops',
    'linux', 'unix', 'nginx', 'apache',
    # Mobile
    'android', 'ios', 'react native', 'flutter', 'xamarin',
    # Tools
    'git', 'github', 'gitlab', 'jira', 'confluence', 'postman', 'swagger',
    'vs code', 'intellij', 'eclipse', 'vim', 'jupyter', 'tableau', 'power bi',
    'excel', 'word', 'figma', 'adobe xd',
    # Concepts
    'oop', 'object oriented', 'functional programming', 'design patterns',
    'microservices', 'serverless', 'agile', 'scrum', 'tdd', 'bdd',
    'data structures', 'algorithms', 'system design', 'distributed systems',
    'blockchain', 'cybersecurity', 'networking', 'linux administration',
}

SOFT_SKILLS = {
    'communication', 'teamwork', 'leadership', 'problem solving', 'problem-solving',
    'critical thinking', 'time management', 'adaptability', 'creativity',
    'collaboration', 'interpersonal', 'presentation', 'negotiation', 'mentoring',
    'project management', 'analytical', 'detail oriented', 'detail-oriented',
    'self motivated', 'self-motivated', 'fast learner', 'quick learner',
    'multitasking', 'prioritization', 'decision making', 'conflict resolution',
    'empathy', 'active listening', 'customer service', 'research', 'initiative',
}

DEGREE_KEYWORDS = {
    'b.tech', 'btech', 'b.e.', 'be', 'bachelor', 'b.sc', 'bsc', 'b.s.', 'bs',
    'mtech', 'm.tech', 'master', 'm.sc', 'msc', 'm.s.', 'ms', 'mba', 'phd',
    'diploma', 'associate', '12th', '10th', 'higher secondary', 'secondary',
    'computer science', 'information technology', 'engineering', 'mathematics',
}

SECTION_WEIGHTS = {
    'contact': 10,
    'objective': 5,
    'education': 15,
    'experience': 25,
    'skills': 20,
    'projects': 15,
    'certifications': 5,
    'achievements': 5,
}


# ─── Core Analysis ─────────────────────────────────────────────────────────────

def extract_skills(text: str) -> Dict[str, List[str]]:
    """Extract technical and soft skills from resume text."""
    text_lower = text.lower()

    found_technical = []
    for skill in TECHNICAL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_technical.append(skill.title() if len(skill.split()) == 1 else skill.title())

    found_soft = []
    for skill in SOFT_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_soft.append(skill.title())

    # Deduplicate while preserving order
    seen = set()
    unique_technical = []
    for s in found_technical:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_technical.append(s)

    seen = set()
    unique_soft = []
    for s in found_soft:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique_soft.append(s)

    return {
        'technical': unique_technical,
        'soft': unique_soft,
    }


def extract_education(text: str, sections: dict) -> List[Dict]:
    """Extract education entries."""
    edu_text = sections.get('education', '') or text
    entries = []

    # Pattern for degrees
    lines = edu_text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in DEGREE_KEYWORDS):
            entry = {
                'raw': line.strip(),
                'degree': extract_degree(line),
                'institution': extract_institution(line),
                'year': extract_year(line),
            }
            if entry['degree'] or entry['institution']:
                entries.append(entry)
            elif entry['raw']:
                entry['degree'] = entry['raw']
                entries.append(entry)

    return entries[:5]  # cap at 5 entries


def extract_degree(line: str) -> str:
    """Extract degree type from a line."""
    degree_map = {
        r'b\.?tech|bachelor.*tech': 'B.Tech',
        r'b\.?e\.?(?!\w)|bachelor.*engineering': 'B.E.',
        r'b\.?sc|bachelor.*science|b\.s\.': 'B.Sc.',
        r'm\.?tech|master.*tech': 'M.Tech',
        r'm\.?sc|master.*science|m\.s\.': 'M.Sc.',
        r'mba': 'MBA',
        r'ph\.?d': 'Ph.D',
        r'diploma': 'Diploma',
        r'10th|ssc|matriculation': '10th Standard',
        r'12th|hsc|higher secondary|intermediate': '12th Standard',
    }
    line_lower = line.lower()
    for pattern, degree in degree_map.items():
        if re.search(pattern, line_lower):
            return degree
    return ''


def extract_institution(line: str) -> str:
    """Extract institution name from a line."""
    institution_keywords = ['university', 'college', 'institute', 'school', 'iit', 'nit', 'bits']
    words = line.split()
    for i, word in enumerate(words):
        if any(kw in word.lower() for kw in institution_keywords):
            start = max(0, i - 2)
            end = min(len(words), i + 3)
            return ' '.join(words[start:end])
    return ''


def extract_year(line: str) -> str:
    """Extract year(s) from a line."""
    years = re.findall(r'\b(19|20)\d{2}\b', line)
    if len(years) >= 2:
        return f"{years[0]} – {years[-1]}"
    elif years:
        return years[0]
    return ''


def extract_experience(text: str, sections: dict) -> List[Dict]:
    """Extract work experience entries."""
    exp_text = sections.get('experience', '') or ''
    entries = []

    if not exp_text:
        return entries

    # Split by common patterns (company name is usually at start of line, dates follow)
    chunks = re.split(r'\n(?=[A-Z][^\n]{5,60}\n)', exp_text)

    for chunk in chunks[:8]:
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        if not lines:
            continue
        entry = {
            'title': '',
            'company': '',
            'duration': '',
            'responsibilities': [],
        }
        for line in lines:
            years = re.findall(r'\b(19|20)\d{2}\b', line)
            if years:
                entry['duration'] = line
            elif not entry['title'] and len(line.split()) <= 8:
                entry['title'] = line
            elif not entry['company'] and len(line.split()) <= 8:
                entry['company'] = line
            elif line.startswith(('•', '-', '*', '–', '▪')):
                entry['responsibilities'].append(line.lstrip('•-*–▪ '))
        if entry['title'] or entry['company']:
            entries.append(entry)

    return entries


def extract_projects(text: str, sections: dict) -> List[Dict]:
    """Extract project entries."""
    proj_text = sections.get('projects', '') or ''
    entries = []

    lines = [l.strip() for l in proj_text.split('\n') if l.strip()]
    current = None
    for line in lines:
        if len(line.split()) <= 8 and not line.startswith(('•', '-', '*')):
            if current:
                entries.append(current)
            current = {'name': line, 'description': [], 'technologies': []}
        elif current:
            tech = extract_tech_from_line(line)
            if tech:
                current['technologies'].extend(tech)
            current['description'].append(line.lstrip('•-*–▪ '))

    if current:
        entries.append(current)

    return entries[:6]


def extract_tech_from_line(line: str) -> List[str]:
    """Extract tech keywords mentioned in a single line."""
    found = []
    line_lower = line.lower()
    for skill in TECHNICAL_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', line_lower):
            found.append(skill.title())
    return found


def score_resume(parsed: dict, sections: dict, skills: dict) -> Dict[str, Any]:
    """Compute individual section scores and overall quality score."""
    text = parsed.get('raw_text', '')
    word_count = parsed.get('word_count', 0)
    contact = parsed.get('contact', {})

    # --- Contact / Header Score ---
    contact_score = 0
    if contact.get('email'):
        contact_score += 30
    if contact.get('phone'):
        contact_score += 30
    if contact.get('linkedin'):
        contact_score += 20
    if contact.get('github'):
        contact_score += 20
    contact_score = min(contact_score, 100)

    # --- Education Score ---
    education_score = 0
    edu_text = sections.get('education', '')
    if edu_text:
        education_score = 50
        if any(kw in edu_text.lower() for kw in ['cgpa', 'gpa', 'percentage', '%']):
            education_score += 25
        if extract_year(edu_text):
            education_score += 25
    education_score = min(education_score, 100)

    # --- Skills Score ---
    tech_count = len(skills.get('technical', []))
    soft_count = len(skills.get('soft', []))
    skills_score = min(tech_count * 5, 70) + min(soft_count * 5, 30)
    skills_score = min(skills_score, 100)

    # --- Experience Score ---
    experience_score = 0
    exp_text = sections.get('experience', '')
    if exp_text:
        experience_score = 40
        bullets = len(re.findall(r'[•\-\*▪]', exp_text))
        experience_score += min(bullets * 5, 40)
        if re.search(r'\b(19|20)\d{2}\b', exp_text):
            experience_score += 20
    experience_score = min(experience_score, 100)

    # --- Projects Score ---
    projects_score = 0
    proj_text = sections.get('projects', '')
    if proj_text:
        projects_score = 40
        projects_score += min(len(extract_tech_from_line(proj_text)) * 5, 40)
        if len(proj_text.split('\n')) > 3:
            projects_score += 20
    projects_score = min(projects_score, 100)

    # --- Keywords Score ---
    high_value_keywords = [
        'developed', 'implemented', 'designed', 'built', 'created', 'led',
        'managed', 'optimized', 'improved', 'achieved', 'deployed', 'integrated',
        'automated', 'analyzed', 'collaborated', 'delivered', 'increased', 'reduced',
    ]
    text_lower = text.lower()
    keyword_hits = sum(1 for kw in high_value_keywords if kw in text_lower)
    keywords_score = min(keyword_hits * 7, 100)

    # --- ATS Score ---
    ats_score = compute_ats_score(text, sections, skills, contact)

    # --- Formatting Score ---
    formatting_score = compute_formatting_score(text, word_count, sections)

    # --- Overall Score (weighted) ---
    overall_score = (
        contact_score * 0.08 +
        education_score * 0.12 +
        skills_score * 0.20 +
        experience_score * 0.25 +
        projects_score * 0.15 +
        keywords_score * 0.10 +
        ats_score * 0.10
    )
    overall_score = round(min(overall_score, 100), 1)

    return {
        'overall': overall_score,
        'contact': round(contact_score, 1),
        'education': round(education_score, 1),
        'skills': round(skills_score, 1),
        'experience': round(experience_score, 1),
        'projects': round(projects_score, 1),
        'keywords': round(keywords_score, 1),
        'ats': round(ats_score, 1),
        'formatting': round(formatting_score, 1),
    }


def compute_ats_score(text: str, sections: dict, skills: dict, contact: dict) -> float:
    """Compute ATS compatibility score."""
    score = 50  # baseline

    # Section headers present
    for section in ['education', 'experience', 'skills', 'projects']:
        if sections.get(section):
            score += 8

    # Contact info
    if contact.get('email'):
        score += 5
    if contact.get('phone'):
        score += 5

    # Skills listed
    if len(skills.get('technical', [])) >= 5:
        score += 10

    # Word count — ATS wants 300-800 words ideally
    word_count = len(text.split())
    if 300 <= word_count <= 1000:
        score += 10
    elif word_count < 150:
        score -= 20

    # Penalize for symbols that confuse ATS
    symbol_count = len(re.findall(r'[★☆✓✗→←↑↓]', text))
    score -= min(symbol_count * 2, 15)

    return round(max(min(score, 100), 0), 1)


def compute_formatting_score(text: str, word_count: int, sections: dict) -> float:
    """Compute a formatting quality score."""
    score = 40

    # Has reasonable length
    if 200 <= word_count <= 1000:
        score += 20
    elif word_count > 100:
        score += 10

    # Multiple sections
    section_count = sum(1 for s in ['education', 'experience', 'skills', 'projects', 'certifications']
                        if sections.get(s))
    score += section_count * 6

    # Lines with bullet points
    bullets = len(re.findall(r'^[\s]*[•\-\*▪]', text, re.MULTILINE))
    score += min(bullets * 2, 20)

    return round(min(score, 100), 1)


def generate_strengths(skills: dict, sections: dict, scores: dict) -> List[str]:
    """Generate strengths based on analysis."""
    strengths = []

    if len(skills.get('technical', [])) >= 8:
        strengths.append(f"Strong technical skill set with {len(skills['technical'])} identified technologies")
    elif len(skills.get('technical', [])) >= 4:
        strengths.append(f"Good technical foundation with {len(skills['technical'])} technologies")

    if sections.get('experience') and scores['experience'] >= 60:
        strengths.append("Work/internship experience demonstrates practical exposure")

    if sections.get('projects') and scores['projects'] >= 50:
        strengths.append("Portfolio projects showcase hands-on development skills")

    if sections.get('certifications'):
        strengths.append("Professional certifications add credibility to your profile")

    if len(skills.get('soft', [])) >= 3:
        strengths.append(f"Soft skills like {', '.join(skills['soft'][:3])} highlighted")

    if scores['ats'] >= 70:
        strengths.append("Resume structure is ATS-friendly")

    if scores['keywords'] >= 60:
        strengths.append("Strong use of action verbs and achievement-oriented language")

    return strengths or ["Resume submitted for analysis — see recommendations below"]


def generate_weaknesses(skills: dict, sections: dict, scores: dict, contact: dict) -> List[str]:
    """Generate weaknesses based on analysis."""
    weaknesses = []

    if scores['skills'] < 40:
        weaknesses.append("Limited technical skills listed — consider expanding your skills section")

    if scores['experience'] < 30 and not sections.get('experience'):
        weaknesses.append("No work experience section detected — add internships or part-time roles")

    if scores['projects'] < 30 and not sections.get('projects'):
        weaknesses.append("No projects section — adding projects significantly improves your profile")

    if not contact.get('linkedin'):
        weaknesses.append("LinkedIn profile URL missing — recruiters expect this")

    if not contact.get('github') and any(s in str(skills.get('technical', [])).lower()
                                          for s in ['python', 'java', 'javascript', 'react', 'github']):
        weaknesses.append("GitHub profile not linked — essential for technical roles")

    if scores['keywords'] < 40:
        weaknesses.append("Lacks strong action verbs (developed, implemented, achieved, optimized, etc.)")

    if scores['ats'] < 50:
        weaknesses.append("ATS compatibility is low — resume may be filtered before reaching recruiters")

    if scores['formatting'] < 50:
        weaknesses.append("Resume formatting could be improved for better readability")

    return weaknesses


def generate_recommendations(skills: dict, sections: dict, scores: dict, contact: dict) -> List[str]:
    """Generate actionable recommendations."""
    recs = []

    if not contact.get('linkedin'):
        recs.append("Add your LinkedIn profile URL to the header section")

    if not contact.get('github'):
        recs.append("Add your GitHub profile to showcase your code and projects")

    if scores['skills'] < 60:
        recs.append("Expand your skills section with specific frameworks, tools, and technologies you've used")

    if not sections.get('projects'):
        recs.append("Add a Projects section with 2-3 projects including technologies used and GitHub links")

    if scores['keywords'] < 50:
        recs.append("Use action verbs: developed, implemented, designed, built, deployed, optimized")

    if scores['ats'] < 60:
        recs.append("Improve ATS compatibility: use standard section headers and avoid complex formatting")

    if not sections.get('certifications'):
        recs.append("Consider adding certifications (Google, AWS, Coursera, etc.) to boost credibility")

    recs.append("Quantify achievements: 'Reduced load time by 30%' is stronger than 'Improved performance'")
    recs.append("Tailor your resume keywords to match each specific job description")

    return recs


def analyze_resume(parsed: dict) -> dict:
    """
    Main analysis function. Returns complete analysis result dict.
    """
    text = parsed.get('raw_text', '')
    sections = parsed.get('sections', {})
    contact = parsed.get('contact', {})

    skills = extract_skills(text)
    education = extract_education(text, sections)
    experience = extract_experience(text, sections)
    projects = extract_projects(text, sections)
    scores = score_resume(parsed, sections, skills)

    strengths = generate_strengths(skills, sections, scores)
    weaknesses = generate_weaknesses(skills, sections, scores, contact)
    recommendations = generate_recommendations(skills, sections, scores, contact)

    # Keywords found (top action words)
    action_words = ['developed', 'implemented', 'designed', 'built', 'created', 'led',
                    'managed', 'optimized', 'improved', 'achieved', 'deployed', 'integrated',
                    'automated', 'analyzed', 'collaborated', 'delivered']
    text_lower = text.lower()
    keywords_found = [w.capitalize() for w in action_words if w in text_lower]

    return {
        'scores': scores,
        'technical_skills': skills['technical'],
        'soft_skills': skills['soft'],
        'education': education,
        'experience': experience,
        'projects': projects,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'recommendations': recommendations,
        'keywords_found': keywords_found,
        'total_skills': len(skills['technical']) + len(skills['soft']),
    }
