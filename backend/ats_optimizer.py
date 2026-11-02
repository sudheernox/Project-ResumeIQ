"""
ATS Optimizer — analyzes ATS compatibility and suggests improvements
"""
import re
from typing import List, Dict, Any
from .resume_analyzer import extract_skills, TECHNICAL_SKILLS


# Common ATS-critical keywords by role
ATS_KEYWORDS = {
    'general': [
        'managed', 'developed', 'designed', 'implemented', 'led', 'created',
        'built', 'analyzed', 'optimized', 'delivered', 'collaborated', 'achieved',
        'increased', 'reduced', 'improved', 'coordinated', 'launched', 'deployed',
    ],
    'technical': [
        'python', 'java', 'javascript', 'sql', 'git', 'api', 'database',
        'cloud', 'agile', 'devops', 'machine learning', 'data analysis',
    ],
    'soft': [
        'leadership', 'communication', 'teamwork', 'problem-solving',
        'analytical', 'collaboration', 'project management',
    ],
}

# ATS-problematic formatting patterns
FORMATTING_ISSUES = [
    (r'[★☆✓✗→←↑↓►◄●○■□]', "Special symbols/icons may confuse ATS parsers"),
    (r'\|', "Pipe characters in text can cause ATS parsing errors"),
    (r'(?i)(header|footer)', "Content in headers/footers is often missed by ATS"),
    (r'\btable\b', "Tables can confuse some ATS systems — prefer plain lists"),
    (r'[^\x00-\x7F]', "Non-ASCII characters may not parse correctly"),
]

WEAK_VERBS = ['worked', 'helped', 'assisted', 'did', 'made', 'got', 'used', 'tried', 'involved in', 'responsible for']
STRONG_VERB_MAP = {
    'worked on': 'developed', 'helped': 'collaborated on',
    'assisted': 'supported', 'did': 'executed', 'made': 'built',
    'got': 'achieved', 'used': 'utilized', 'tried': 'implemented',
    'involved in': 'contributed to', 'responsible for': 'managed',
}


def analyze_ats(resume_text: str, target_role: str = '') -> Dict[str, Any]:
    """
    Comprehensive ATS compatibility analysis.
    """
    text_lower = resume_text.lower()
    issues = []
    recommendations = []
    missing_keywords = []
    formatting_issues = []

    # 1. Check for formatting problems
    symbol_count = len(re.findall(r'[★☆✓✗→←↑↓►◄●○■□]', resume_text))
    if symbol_count > 0:
        formatting_issues.append({
            'issue': 'Special symbols detected',
            'detail': f"Found {symbol_count} special symbols/icons that ATS parsers cannot read",
            'severity': 'high',
        })

    # 2. Check section headers
    standard_sections = {
        'experience': r'\b(experience|work history|employment)\b',
        'education': r'\b(education|academic)\b',
        'skills': r'\b(skills|technical skills|competencies)\b',
        'summary': r'\b(summary|objective|profile|about)\b',
    }
    missing_sections = []
    for section, pattern in standard_sections.items():
        if not re.search(pattern, text_lower):
            missing_sections.append(section.title())

    if missing_sections:
        issues.append({
            'issue': f"Missing standard sections: {', '.join(missing_sections)}",
            'severity': 'high',
            'fix': f"Add these section headers exactly as: {', '.join(missing_sections)}"
        })

    # 3. Word count check
    word_count = len(resume_text.split())
    if word_count < 200:
        issues.append({
            'issue': 'Resume too short',
            'severity': 'high',
            'fix': f"Resume has only {word_count} words. Aim for 400-800 words.",
        })
    elif word_count > 1500:
        issues.append({
            'issue': 'Resume too long',
            'severity': 'medium',
            'fix': f"Resume has {word_count} words. Trim to 1 page (500-800 words) for entry-level.",
        })

    # 4. Check for contact info
    if not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text):
        issues.append({
            'issue': 'Email address missing',
            'severity': 'high',
            'fix': 'Add your professional email address at the top of the resume',
        })

    if not re.search(r'(\+?\d[\d\s\-\.]{8,})', resume_text):
        issues.append({
            'issue': 'Phone number missing',
            'severity': 'medium',
            'fix': 'Add your phone number in the header',
        })

    # 5. Check for weak verbs
    weak_found = []
    for verb in WEAK_VERBS:
        if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
            weak_found.append(verb)

    if weak_found:
        issues.append({
            'issue': f"Weak action verbs: {', '.join(weak_found[:4])}",
            'severity': 'medium',
            'fix': 'Replace with power verbs: developed, implemented, achieved, designed, optimized',
        })

    # 6. Missing keywords
    general_keywords = ATS_KEYWORDS['general']
    found_kw = [kw for kw in general_keywords if kw in text_lower]
    missing_kw = [kw for kw in general_keywords if kw not in text_lower]
    missing_keywords = missing_kw[:10]

    if len(found_kw) < 5:
        issues.append({
            'issue': 'Few action verbs detected',
            'severity': 'medium',
            'fix': f"Add more action verbs. Missing: {', '.join(missing_kw[:5])}",
        })

    # 7. Quantification check
    has_numbers = bool(re.search(r'\b\d+[%+x]?\b', resume_text))
    if not has_numbers:
        issues.append({
            'issue': 'No quantifiable achievements',
            'severity': 'medium',
            'fix': "Add metrics: 'Improved system speed by 40%', 'Led a team of 5 developers'",
        })

    # 8. LinkedIn/GitHub
    if not re.search(r'linkedin', text_lower):
        recommendations.append("Add LinkedIn profile URL — many ATS pull professional network data")

    if not re.search(r'github', text_lower):
        recommendations.append("Add GitHub profile URL for technical roles")

    # 9. Bullet points
    bullet_count = len(re.findall(r'^[\s]*[•\-\*▪]', resume_text, re.MULTILINE))
    if bullet_count < 5:
        recommendations.append("Use bullet points (•) for experience and project descriptions — improves ATS readability")

    # 10. Before/After examples
    before_after = generate_before_after_examples(resume_text)

    # Compute ATS score
    ats_score = compute_ats_score_from_issues(issues, word_count, bullet_count)

    return {
        'ats_score': ats_score,
        'issues': issues,
        'formatting_issues': formatting_issues,
        'missing_keywords': missing_keywords,
        'recommendations': recommendations,
        'before_after_examples': before_after,
        'quick_wins': generate_quick_wins(issues),
        'ats_disclaimer': 'ATS Compatibility Estimate: This evaluation is an algorithmic estimate modeled on leading applicant tracking systems (Workday, Greenhouse, Taleo, Lever). Real proprietary employer ATS platforms vary based on individual recruiter configurations.',
        'keyword_density': {
            'found': found_kw,
            'missing': missing_kw[:8],
            'coverage': f"{len(found_kw)}/{len(general_keywords)}",
        },
    }


def compute_ats_score_from_issues(issues: list, word_count: int, bullet_count: int) -> float:
    """Compute realistic ATS score based on identified issues (never automatically 100%, realistic max 92.5%)."""
    score = 88.0

    for issue in issues:
        if issue['severity'] == 'high':
            score -= 15
        elif issue['severity'] == 'medium':
            score -= 8
        else:
            score -= 3

    if word_count < 150:
        score -= 25
    elif word_count < 250:
        score -= 10
    elif 350 <= word_count <= 850:
        score += 3

    if bullet_count >= 8:
        score += 2
    elif bullet_count == 0:
        score -= 15

    return round(max(min(score, 92.5), 15.0), 1)


def generate_before_after_examples(resume_text: str) -> List[Dict[str, str]]:
    """Generate before/after bullet point improvement examples."""
    examples = []

    # Find bullet lines in the resume
    bullets = re.findall(r'[•\-\*▪]\s*(.+)', resume_text)

    for bullet in bullets[:3]:
        original = bullet.strip()
        improved = improve_bullet(original)
        if improved != original:
            examples.append({
                'before': f"• {original}",
                'after': f"• {improved}",
            })

    # Add generic examples if we couldn't find enough
    if len(examples) < 2:
        examples.extend([
            {
                'before': "• Responsible for developing backend APIs",
                'after': "• Designed and implemented 15+ RESTful APIs using Python/Flask, reducing response time by 30%",
            },
            {
                'before': "• Worked on database optimization",
                'after': "• Optimized MySQL queries and implemented indexing strategies, improving performance by 40%",
            },
            {
                'before': "• Helped team with front-end development",
                'after': "• Collaborated with a 5-member team to build responsive UI components using React and Tailwind CSS",
            },
        ])

    return examples[:4]


def improve_bullet(bullet: str) -> str:
    """Improve a single bullet point."""
    bullet_lower = bullet.lower()

    for weak, strong in STRONG_VERB_MAP.items():
        if bullet_lower.startswith(weak):
            return bullet.replace(bullet.split()[0], strong.split()[0], 1)

    # Suggest adding metrics if none present
    if not re.search(r'\d+', bullet):
        return bullet.rstrip('.') + " (add metrics: %, count, timeframe)"

    return bullet


def generate_quick_wins(issues: list) -> List[str]:
    """Generate top 5 quick actionable wins."""
    wins = []
    for issue in sorted(issues, key=lambda x: 0 if x['severity'] == 'high' else 1)[:5]:
        wins.append(issue['fix'])
    return wins
