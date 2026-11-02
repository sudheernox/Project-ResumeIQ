"""
Skill Gap Analyzer — identifies gaps between current skills and career role requirements
"""
from typing import List, Dict, Any
from collections import Counter
from .resume_analyzer import extract_skills
from .job_matcher import ROLE_PROFILES


# ─── Career skill requirements (detailed) ────────────────────────────────────

CAREER_SKILL_MATRIX = {
    'Software Developer': {
        'Programming Languages':   {'required': ['Python', 'Java', 'JavaScript', 'C++'], 'weight': 25},
        'Web Technologies':        {'required': ['HTML', 'CSS', 'REST', 'Git'], 'weight': 20},
        'Databases':               {'required': ['SQL', 'MySQL', 'MongoDB'], 'weight': 15},
        'Frameworks':              {'required': ['React', 'Node.js', 'Spring', 'Django'], 'weight': 20},
        'DevOps & Tools':          {'required': ['Docker', 'Git', 'Linux', 'CI/CD'], 'weight': 10},
        'CS Fundamentals':         {'required': ['Data Structures', 'Algorithms', 'OOP', 'Design Patterns'], 'weight': 10},
    },
    'Web Developer': {
        'Frontend':                {'required': ['HTML5', 'CSS3', 'JavaScript', 'React', 'Bootstrap'], 'weight': 30},
        'Backend':                 {'required': ['Node.js', 'Python', 'REST', 'Express'], 'weight': 25},
        'Databases':               {'required': ['SQL', 'MongoDB', 'MySQL'], 'weight': 15},
        'Version Control':         {'required': ['Git', 'GitHub'], 'weight': 10},
        'UI/UX Tools':             {'required': ['Figma', 'Adobe XD', 'Tailwind'], 'weight': 10},
        'Performance':             {'required': ['SEO', 'Caching', 'Webpack'], 'weight': 10},
    },
    'Data Analyst': {
        'Programming':             {'required': ['Python', 'R', 'SQL'], 'weight': 25},
        'Data Processing':         {'required': ['Pandas', 'NumPy', 'Excel'], 'weight': 25},
        'Visualization':           {'required': ['Matplotlib', 'Tableau', 'Power BI', 'Seaborn'], 'weight': 20},
        'Statistics':              {'required': ['Statistics', 'Probability', 'Hypothesis Testing'], 'weight': 15},
        'Databases':               {'required': ['MySQL', 'PostgreSQL', 'MongoDB'], 'weight': 15},
    },
    'Machine Learning Engineer': {
        'ML Frameworks':           {'required': ['TensorFlow', 'PyTorch', 'Scikit-Learn', 'Keras'], 'weight': 25},
        'Programming':             {'required': ['Python', 'R', 'Scala'], 'weight': 20},
        'Data Processing':         {'required': ['Pandas', 'NumPy', 'Spark'], 'weight': 15},
        'Mathematics':             {'required': ['Statistics', 'Linear Algebra', 'Calculus'], 'weight': 20},
        'MLOps':                   {'required': ['Docker', 'Kubernetes', 'AWS', 'MLflow'], 'weight': 10},
        'Specializations':         {'required': ['NLP', 'Computer Vision', 'Deep Learning'], 'weight': 10},
    },
    'QA Engineer': {
        'Testing Types':           {'required': ['Manual Testing', 'Automation Testing', 'Performance Testing'], 'weight': 30},
        'Automation Tools':        {'required': ['Selenium', 'Pytest', 'JUnit', 'TestNG'], 'weight': 25},
        'API Testing':             {'required': ['Postman', 'Rest Assured', 'API Testing'], 'weight': 20},
        'Programming':             {'required': ['Python', 'Java', 'JavaScript'], 'weight': 15},
        'Project Tools':           {'required': ['Jira', 'Git', 'Agile', 'Scrum'], 'weight': 10},
    },
}


def compute_skill_gap(resume_text: str, career_role: str,
                       custom_jd: str = '') -> Dict[str, Any]:
    """
    Compute skill gap between resume and career role or custom JD.
    Returns gap analysis with radar chart data.
    """
    skills = extract_skills(resume_text)
    resume_tech_lower = {s.lower() for s in skills['technical']}
    resume_soft_lower = {s.lower() for s in skills['soft']}
    resume_all_lower = resume_tech_lower | resume_soft_lower

    matrix = dict(CAREER_SKILL_MATRIX.get(career_role, CAREER_SKILL_MATRIX['Software Developer']))
    role_profile = ROLE_PROFILES.get(career_role, {})

    # If custom JD is supplied, extract skills and incorporate as a prominent category
    if custom_jd and custom_jd.strip():
        jd_skills = extract_skills(custom_jd)
        custom_tech = jd_skills.get('technical', [])
        if custom_tech:
            matrix['Job Description Specific'] = {
                'required': custom_tech[:8],
                'weight': 30
            }
            # Normalize other weights
            for cat in list(matrix.keys()):
                if cat != 'Job Description Specific':
                    matrix[cat]['weight'] = max(round(matrix[cat]['weight'] * 0.7), 5)

    # Gap by category
    category_analysis = []
    radar_labels = []
    radar_current = []
    radar_required = []

    existing_skills = []
    missing_technical = []
    skills_to_improve = []

    for category, data in matrix.items():
        required_skills = data['required']
        weight = data.get('weight', 20)

        matched = []
        missing = []
        for skill in required_skills:
            skill_lower = skill.lower()
            found = False
            for res in resume_all_lower:
                if skill_lower == res or skill_lower in res or res in skill_lower:
                    found = True
                    break
            if found:
                matched.append(skill)
                existing_skills.append(skill)
            else:
                missing.append(skill)
                missing_technical.append(skill)

        category_score = round((len(matched) / max(len(required_skills), 1)) * 100, 1)
        category_required = 100

        radar_labels.append(category)
        radar_current.append(category_score)
        radar_required.append(category_required)

        category_analysis.append({
            'category': category,
            'matched': matched,
            'missing': missing,
            'score': category_score,
            'required_score': category_required,
            'weight': weight,
        })

    # Soft skills gap
    role_soft = role_profile.get('soft', ['Communication', 'Teamwork', 'Problem Solving'])
    missing_soft = [s.title() for s in role_soft if s.lower() not in resume_all_lower]

    # Determine skills needing improvement (partially present)
    for skill in list(missing_technical):
        for res in resume_all_lower:
            if skill.lower() in res or res in skill.lower():
                skills_to_improve.append(skill)
                if skill in missing_technical:
                    missing_technical.remove(skill)
                break

    # Priority skills (most critical missing)
    all_missing_flat = [s for cat in category_analysis for s in cat['missing']]
    priority_skills = [s for s, count in Counter(all_missing_flat).most_common(5)]
    if not priority_skills and missing_technical:
        priority_skills = missing_technical[:4]

    # Overall gap score
    total_weight = sum(cat['weight'] for cat in category_analysis) or 1
    weighted_score = sum(
        cat['score'] * (cat['weight'] / total_weight)
        for cat in category_analysis
    )
    overall_coverage = round(weighted_score, 1)

    return {
        'career_role': career_role,
        'custom_jd': custom_jd,
        'overall_coverage': overall_coverage,
        'category_analysis': category_analysis,
        'existing_skills': list(dict.fromkeys(existing_skills)),
        'missing_technical': list(dict.fromkeys(missing_technical))[:15],
        'missing_soft': missing_soft[:8],
        'skills_to_improve': list(dict.fromkeys(skills_to_improve))[:8],
        'priority_skills': priority_skills,
        'radar_data': {
            'labels': radar_labels,
            'current': radar_current,
            'required': radar_required,
        },
        'total_missing': len(missing_technical) + len(missing_soft),
    }
