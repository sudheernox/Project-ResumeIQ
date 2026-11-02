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
    """
    Compute a balanced, realistic resume quality score across 6 weighted categories:
    1. Skills & Keyword Relevance: 25%
    2. Experience & Achievements: 20%
    3. Resume Formatting & Structure: 20%
    4. Education & Projects: 15%
    5. ATS Readability & Parsing Compatibility: 15%
    6. Contact Information & Completeness: 5%

    Rules:
    - Never automatically give 100%. Max realistic score capped at 93.5%.
    - A badly formatted resume receives an appropriately low score (30-50%).
    - Show category-wise scores with explicit deductions and improvement suggestions.
    """
    text = parsed.get('raw_text', '')
    word_count = parsed.get('word_count', 0)
    contact = parsed.get('contact') or {
        'email': parsed.get('email', ''),
        'phone': parsed.get('phone', ''),
        'linkedin': parsed.get('linkedin', ''),
        'github': parsed.get('github', '')
    }
    text_lower = text.lower()

    tech_skills = skills.get('technical', [])
    soft_skills = skills.get('soft', [])

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 1: Skills & Keyword Relevance (Weight: 25%)
    # ─────────────────────────────────────────────────────────────────────────────
    skills_score = 0.0
    skills_deductions = []
    skills_suggestions = []

    tech_count = len(tech_skills)
    if tech_count == 0:
        skills_score = 15.0
        skills_deductions.append("No technical skills detected in resume (-35 pts)")
        skills_suggestions.append("Add a dedicated Skills section detailing your programming languages, tools, and platforms.")
    elif tech_count <= 3:
        skills_score = 45.0
        skills_deductions.append(f"Only {tech_count} technical skills identified (-20 pts)")
        skills_suggestions.append("Expand technical competencies to include relevant frameworks, libraries, and tools.")
    elif tech_count <= 7:
        skills_score = 70.0
        skills_deductions.append(f"Found {tech_count} technical skills; target roles typically expect 8-15 (-10 pts)")
        skills_suggestions.append("Incorporate databases, cloud providers, and DevOps/testing tools into your skills inventory.")
    elif tech_count <= 14:
        skills_score = 86.0
    else:
        skills_score = 92.0

    soft_count = len(soft_skills)
    if soft_count == 0:
        skills_score -= 8.0
        skills_deductions.append("No professional soft skills found (-8 pts)")
        skills_suggestions.append("Highlight soft skills such as leadership, cross-functional collaboration, or problem solving.")
    else:
        skills_score += min(soft_count * 2.0, 8.0)

    action_words = [
        'developed', 'implemented', 'designed', 'built', 'created', 'led',
        'managed', 'optimized', 'improved', 'achieved', 'deployed', 'integrated',
        'automated', 'analyzed', 'collaborated', 'spearheaded', 'architected', 'orchestrated'
    ]
    verb_hits = sum(1 for w in action_words if w in text_lower)
    if verb_hits < 3:
        skills_score -= 10.0
        skills_deductions.append("Low action verb density across bullet points (-10 pts)")
        skills_suggestions.append("Begin accomplishment statements with impactful action verbs (e.g., Engineered, Spearheaded, Automated).")

    weak_verbs = ['worked on', 'worked', 'helped with', 'helped', 'assisted', 'did', 'made', 'involved in', 'responsible for']
    weak_found = [w for w in weak_verbs if re.search(r'\b' + re.escape(w) + r'\b', text_lower)]
    if weak_found:
        pen = min(len(weak_found) * 3, 9)
        skills_score -= pen
        skills_deductions.append(f"Passive language detected: {', '.join(weak_found[:3])} (-{pen} pts)")
        skills_suggestions.append("Replace passive phrases ('responsible for', 'worked on') with dynamic action verbs.")

    skills_score = max(min(skills_score, 94.0), 10.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 2: Experience & Achievements (Weight: 20%)
    # ─────────────────────────────────────────────────────────────────────────────
    exp_text = sections.get('experience', '')
    if not exp_text or len(exp_text.strip()) < 30:
        # Fallback to search in raw_text if experience keywords exist
        if 'experience' in text_lower or 'work history' in text_lower or 'employment' in text_lower:
            exp_text = text

    exp_score = 0.0
    exp_deductions = []
    exp_suggestions = []

    if not exp_text or len(exp_text.strip()) < 30:
        exp_score = 25.0
        exp_deductions.append("Dedicated Work Experience or Internship section is missing or empty (-50 pts)")
        exp_suggestions.append("Add relevant work experience, internships, freelance projects, or leadership roles.")
    else:
        exp_score = 45.0
        # Quantifiable achievements
        metric_matches = re.findall(
            r'(\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?(?:[MBk])?|\b\d+x\b|\b\d+(?:,\d+)?\s*(?:users|clients|requests|ms|seconds|engineers|customers|transactions|million|billion)\b|\b\d{2,}\+?\b)',
            exp_text, re.IGNORECASE
        )
        if len(metric_matches) == 0:
            exp_deductions.append("No quantifiable metrics, percentages, or measurable outcomes found in experience (-30 pts)")
            exp_suggestions.append("Quantify achievements (e.g., 'Improved query performance by 40%', 'Supported 10,000+ monthly active users').")
        elif len(metric_matches) <= 2:
            exp_score += 20.0
            exp_deductions.append("Few quantifiable metrics in experience bullets (-10 pts)")
            exp_suggestions.append("Add measurable outcomes to additional bullet points to prove tangible business value.")
        else:
            exp_score += 35.0

        bullets_exp = len(re.findall(r'[•\-\*▪]', exp_text))
        if bullets_exp < 2:
            exp_score -= 10.0
            exp_deductions.append("Experience section lacks structured bullet point depth (-10 pts)")
            exp_suggestions.append("Organize work responsibilities into 3-5 concise, outcome-focused bullet points per role.")
        else:
            exp_score += 10.0

        if re.search(r'\b(19|20)\d{2}\b', exp_text):
            exp_score += 5.0
        else:
            exp_deductions.append("Employment dates / tenure timeline missing or ambiguous (-8 pts)")
            exp_suggestions.append("Include clear start and end dates (Month/Year) for each position.")

    exp_score = max(min(exp_score, 93.0), 15.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 3: Resume Formatting & Structure (Weight: 20%)
    # ─────────────────────────────────────────────────────────────────────────────
    form_score = 90.0
    form_deductions = []
    form_suggestions = []

    for s_name in ['experience', 'education', 'skills', 'projects']:
        if not sections.get(s_name):
            form_score -= 15.0
            form_deductions.append(f"Missing standard '{s_name.title()}' section header (-15 pts)")
            form_suggestions.append(f"Create a clear, dedicated '{s_name.title()}' section header.")

    if not sections.get('objective'):
        form_score -= 5.0
        form_deductions.append("Missing Professional Summary or Career Objective (-5 pts)")
        form_suggestions.append("Add a 2-3 line Professional Summary at the top summarizing your core expertise and career goals.")

    if word_count < 150:
        form_score -= 35.0
        form_deductions.append(f"Resume text is critically brief ({word_count} words; aim for 400-800 words) (-35 pts)")
        form_suggestions.append("Expand your resume with project details, accomplishments, and skills to provide sufficient signal for recruiters.")
    elif word_count < 250:
        form_score -= 15.0
        form_deductions.append(f"Resume length is below ideal threshold ({word_count} words) (-15 pts)")
        form_suggestions.append("Elaborate on your project implementations and role contributions to reach 450-700 words.")
    elif word_count > 1200:
        form_score -= 10.0
        form_deductions.append(f"Resume is lengthy ({word_count} words; consider trimming to 1-2 pages) (-10 pts)")
        form_suggestions.append("Condense older roles and remove secondary details to keep within 1-2 pages.")

    tot_bullets = len(re.findall(r'[•\-\*▪]', text))
    if tot_bullets == 0:
        form_score -= 20.0
        form_deductions.append("No bullet points detected across resume (-20 pts)")
        form_suggestions.append("Use standard bullet points (•) for experience and project entries instead of dense paragraphs.")
    elif tot_bullets < 4:
        form_score -= 10.0
        form_deductions.append(f"Sparse bullet point usage ({tot_bullets} bullets detected) (-10 pts)")
        form_suggestions.append("Structure role responsibilities and project features into bullet lists.")

    pipes_count = text.count('|')
    if pipes_count > 10:
        form_score -= 5.0
        form_deductions.append("Excessive pipe (|) delimiters may cause text flow merging in certain ATS parsers (-5 pts)")
        form_suggestions.append("Use tabs, commas, or bullet characters instead of frequent pipe symbols.")

    form_score = max(min(form_score, 93.0), 15.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 4: Education & Projects (Weight: 15%)
    # ─────────────────────────────────────────────────────────────────────────────
    edu_proj_score = 0.0
    edu_deductions = []
    edu_suggestions = []

    edu_text = sections.get('education', '')
    if edu_text:
        edu_proj_score += 20.0
        if re.search(r'(b\.?tech|bachelor|b\.?e|b\.?s|master|m\.?tech|m\.?s|phd|diploma|associate|degree)', edu_text, re.IGNORECASE):
            edu_proj_score += 15.0
        else:
            edu_deductions.append("Degree name/level not clearly recognizable (-15 pts)")
            edu_suggestions.append("Explicitly state degree type (e.g. 'Bachelor of Technology in Computer Science').")

        if re.search(r'(university|college|institute|school|academy)', edu_text, re.IGNORECASE):
            edu_proj_score += 10.0
        else:
            edu_deductions.append("Institution / university name missing or ambiguous (-10 pts)")
            edu_suggestions.append("Clearly specify university or accredited institution name.")

        if re.search(r'\b(19|20)\d{2}\b', edu_text):
            edu_proj_score += 10.0
        else:
            edu_deductions.append("Graduation year or date range missing (-5 pts)")
            edu_suggestions.append("Add graduation year or expected graduation date.")
    else:
        edu_deductions.append("Missing Education section (-35 pts)")
        edu_suggestions.append("Add an Education section with your degree, institution, and graduation year.")

    proj_text = sections.get('projects', '')
    if proj_text:
        edu_proj_score += 25.0
        if len(proj_text.split('\n')) > 3:
            edu_proj_score += 15.0
    else:
        edu_deductions.append("Missing Projects section (-30 pts)")
        edu_suggestions.append("Include 2-3 personal or professional projects demonstrating practical implementation of your skills.")

    edu_proj_score = max(min(edu_proj_score, 94.0), 10.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 5: ATS Readability & Parsing Compatibility (Weight: 15%)
    # ─────────────────────────────────────────────────────────────────────────────
    ats_score = 90.0
    ats_deductions = []
    ats_suggestions = []

    sym_count = len(re.findall(r'[★☆✓✗→←↑↓►◄●○■□]', text))
    if sym_count > 0:
        pen = min(sym_count * 5, 25)
        ats_score -= pen
        ats_deductions.append(f"Special symbols/icons ({sym_count} symbols) break ATS tokenizers (-{pen} pts)")
        ats_suggestions.append("Remove decorative symbols, stars, and graphic checkmarks; use standard text bullets (•).")

    missing_core = [s for s in ['experience', 'education', 'skills'] if not sections.get(s)]
    if missing_core:
        pen = len(missing_core) * 8
        ats_score -= pen
        ats_deductions.append(f"Core ATS indexing sections missing: {', '.join(missing_core)} (-{pen} pts)")
        ats_suggestions.append("Include standard section headings that ATS indexers rely on.")

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        frag_lines = sum(1 for l in lines if len(l.split()) <= 2)
        if len(lines) >= 20 and frag_lines / len(lines) > 0.45:
            ats_score -= 15.0
            ats_deductions.append("Fragmented line layout detected (likely multi-column or text boxes) (-15 pts)")
            ats_suggestions.append("Adopt a single-column, left-aligned layout without text boxes or tables for ATS compatibility.")

    non_ascii = len(re.findall(r'[^\x00-\x7F]', text))
    if non_ascii > 10:
        ats_score -= 5.0
        ats_deductions.append("Non-standard character encoding detected (-5 pts)")
        ats_suggestions.append("Save resume in standard UTF-8 text encoding without non-printable glyphs.")

    ats_score = max(min(ats_score, 92.5), 15.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Category 6: Contact Information & Completeness (Weight: 5%)
    # ─────────────────────────────────────────────────────────────────────────────
    contact_score = 100.0
    contact_deductions = []
    contact_suggestions = []

    if not contact.get('email'):
        contact_score -= 35.0
        contact_deductions.append("Professional email address missing (-35 pts)")
        contact_suggestions.append("Place your professional email address prominently at the top header.")
    if not contact.get('phone'):
        contact_score -= 25.0
        contact_deductions.append("Contact phone number missing (-25 pts)")
        contact_suggestions.append("Add a valid phone number with country/area code in the header.")
    if not contact.get('linkedin'):
        contact_score -= 20.0
        contact_deductions.append("LinkedIn profile URL missing (-20 pts)")
        contact_suggestions.append("Include a link to your active LinkedIn profile.")
    if not contact.get('github') and any(s in str(tech_skills).lower() for s in ['python', 'java', 'react', 'git', 'sql']):
        contact_score -= 20.0
        contact_deductions.append("GitHub profile link missing for technical profile (-20 pts)")
        contact_suggestions.append("Add your GitHub profile URL to showcase open-source work and repositories.")

    contact_score = max(min(contact_score, 100.0), 10.0)

    # ─────────────────────────────────────────────────────────────────────────────
    # Composite Overall Score (Weighted)
    # ─────────────────────────────────────────────────────────────────────────────
    raw_overall = (
        skills_score * 0.25 +
        exp_score * 0.20 +
        form_score * 0.20 +
        edu_proj_score * 0.15 +
        ats_score * 0.15 +
        contact_score * 0.05
    )

    # Never automatically give 100%; cap realistic max at 93.5%
    overall = min(round(raw_overall, 1), 93.5)

    category_scores = {
        'skills_relevance': {
            'name': 'Skills & Keyword Relevance',
            'weight': 25,
            'score': round(skills_score, 1),
            'deductions': skills_deductions,
            'suggestions': skills_suggestions,
        },
        'experience_achievements': {
            'name': 'Experience & Achievements',
            'weight': 20,
            'score': round(exp_score, 1),
            'deductions': exp_deductions,
            'suggestions': exp_suggestions,
        },
        'formatting_structure': {
            'name': 'Resume Formatting & Structure',
            'weight': 20,
            'score': round(form_score, 1),
            'deductions': form_deductions,
            'suggestions': form_suggestions,
        },
        'education_projects': {
            'name': 'Education & Projects',
            'weight': 15,
            'score': round(edu_proj_score, 1),
            'deductions': edu_deductions,
            'suggestions': edu_suggestions,
        },
        'ats_compatibility': {
            'name': 'ATS Readability & Parsing',
            'weight': 15,
            'score': round(ats_score, 1),
            'deductions': ats_deductions,
            'suggestions': ats_suggestions,
        },
        'contact_completeness': {
            'name': 'Contact Information & Completeness',
            'weight': 5,
            'score': round(contact_score, 1),
            'deductions': contact_deductions,
            'suggestions': contact_suggestions,
        },
    }

    all_deductions = (
        skills_deductions + exp_deductions + form_deductions +
        edu_deductions + ats_deductions + contact_deductions
    )

    keywords_score = min(verb_hits * 12.0, 92.0)

    return {
        'overall': overall,
        'skills': round(skills_score, 1),
        'experience': round(exp_score, 1),
        'formatting': round(form_score, 1),
        'education': round(edu_proj_score, 1),
        'projects': round(edu_proj_score, 1),
        'education_projects': round(edu_proj_score, 1),
        'ats': round(ats_score, 1),
        'contact': round(contact_score, 1),
        'keywords': round(keywords_score, 1),
        'category_scores': category_scores,
        'deductions_summary': all_deductions,
        'ats_disclaimer': 'ATS Compatibility Estimate: This evaluation is an algorithmic estimate modeled on leading applicant tracking systems (Workday, Greenhouse, Taleo, Lever). Real proprietary employer ATS platforms vary based on individual recruiter configurations.',
    }


def compute_ats_score(text: str, sections: dict, skills: dict, contact: dict) -> float:
    """Compute ATS compatibility score with realistic constraints (capped at 92.5)."""
    score = 90.0

    # Penalize for missing core sections
    missing = [s for s in ['experience', 'education', 'skills'] if not sections.get(s)]
    score -= len(missing) * 10

    # Check symbols
    sym_count = len(re.findall(r'[★☆✓✗→←↑↓►◄●○■□]', text))
    if sym_count > 0:
        score -= min(sym_count * 4, 25)

    # Check word count
    word_count = len(text.split())
    if word_count < 150:
        score -= 30
    elif word_count < 250:
        score -= 15

    # Contact info
    if not contact.get('email'):
        score -= 10
    if not contact.get('phone'):
        score -= 10

    return round(max(min(score, 92.5), 15.0), 1)


def compute_formatting_score(text: str, word_count: int, sections: dict) -> float:
    """Compute formatting quality score with realistic penalties."""
    score = 90.0

    # Core sections
    missing = [s for s in ['experience', 'education', 'skills', 'projects'] if not sections.get(s)]
    score -= len(missing) * 12

    # Length
    if word_count < 150:
        score -= 30
    elif word_count < 250:
        score -= 15
    elif word_count > 1200:
        score -= 10

    # Bullets
    bullets = len(re.findall(r'[•\-\*▪]', text))
    if bullets == 0:
        score -= 20
    elif bullets < 4:
        score -= 10

    return round(max(min(score, 93.0), 15.0), 1)


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
    contact = parsed.get('contact') or {
        'email': parsed.get('email', ''),
        'phone': parsed.get('phone', ''),
        'linkedin': parsed.get('linkedin', ''),
        'github': parsed.get('github', '')
    }

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
        'category_scores': scores.get('category_scores', {}),
        'deductions_summary': scores.get('deductions_summary', []),
        'ats_disclaimer': scores.get('ats_disclaimer', ''),
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
