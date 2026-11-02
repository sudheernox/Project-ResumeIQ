"""
Job Matcher — computes job compatibility score between resume and job description
"""
import re
import math
from typing import List, Dict, Any
from .resume_analyzer import TECHNICAL_SKILLS, SOFT_SKILLS, extract_skills


# ─── Role-specific skill profiles ────────────────────────────────────────────

ROLE_PROFILES = {
    'Software Developer': {
        'required': ['python', 'java', 'javascript', 'git', 'sql', 'data structures', 'algorithms', 'oop'],
        'preferred': ['react', 'nodejs', 'docker', 'aws', 'agile', 'design patterns', 'rest', 'microservices'],
        'soft': ['problem solving', 'teamwork', 'communication', 'analytical'],
    },
    'Web Developer': {
        'required': ['html', 'css', 'javascript', 'git', 'rest', 'sql'],
        'preferred': ['react', 'nodejs', 'bootstrap', 'typescript', 'mongodb', 'tailwind', 'next.js'],
        'soft': ['creativity', 'communication', 'problem solving', 'teamwork'],
    },
    'Data Analyst': {
        'required': ['python', 'sql', 'excel', 'data analysis', 'statistics', 'pandas'],
        'preferred': ['tableau', 'power bi', 'numpy', 'matplotlib', 'r', 'data visualization'],
        'soft': ['analytical', 'communication', 'critical thinking', 'problem solving'],
    },
    'Machine Learning Engineer': {
        'required': ['python', 'machine learning', 'numpy', 'pandas', 'scikit-learn', 'mathematics', 'statistics'],
        'preferred': ['deep learning', 'tensorflow', 'pytorch', 'nlp', 'computer vision', 'docker', 'aws', 'spark'],
        'soft': ['analytical', 'research', 'problem solving', 'critical thinking'],
    },
    'QA Engineer': {
        'required': ['testing', 'manual testing', 'sql', 'git', 'api testing', 'agile'],
        'preferred': ['selenium', 'pytest', 'postman', 'jira', 'automation testing', 'bdd', 'cucumber'],
        'soft': ['detail oriented', 'analytical', 'communication', 'teamwork'],
    },
    'DevOps Engineer': {
        'required': ['linux', 'docker', 'kubernetes', 'ci/cd', 'git', 'bash', 'aws'],
        'preferred': ['terraform', 'ansible', 'jenkins', 'monitoring', 'python', 'nginx'],
        'soft': ['problem solving', 'teamwork', 'communication', 'adaptability'],
    },
    'Full Stack Developer': {
        'required': ['javascript', 'html', 'css', 'sql', 'git', 'rest'],
        'preferred': ['react', 'nodejs', 'python', 'mongodb', 'docker', 'typescript', 'graphql'],
        'soft': ['problem solving', 'communication', 'teamwork', 'time management'],
    },
    'Android Developer': {
        'required': ['android', 'java', 'kotlin', 'xml', 'git'],
        'preferred': ['react native', 'flutter', 'firebase', 'rest', 'mvvm', 'jetpack compose'],
        'soft': ['problem solving', 'creativity', 'teamwork', 'communication'],
    },
}


def extract_job_skills(job_description: str) -> Dict[str, List[str]]:
    """Extract required skills from job description text."""
    jd_lower = job_description.lower()

    required_skills = []
    preferred_skills = []

    # Find required section
    req_match = re.search(r'(required|must have|mandatory|essential|qualifications)[:\s]*(.*?)(?=preferred|nice to have|good to have|responsibilities|$)',
                          jd_lower, re.DOTALL | re.IGNORECASE)
    pref_match = re.search(r'(preferred|nice to have|good to have|bonus|plus)[:\s]*(.*?)(?=\n\n|$)',
                           jd_lower, re.DOTALL | re.IGNORECASE)

    req_text = req_match.group(2) if req_match else jd_lower
    pref_text = pref_match.group(2) if pref_match else ''

    for skill in TECHNICAL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, req_text):
            required_skills.append(skill.title())
        elif pref_text and re.search(pattern, pref_text):
            preferred_skills.append(skill.title())
        elif re.search(pattern, jd_lower):
            required_skills.append(skill.title())

    for skill in SOFT_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, jd_lower):
            preferred_skills.append(skill.title())

    return {
        'required': list(dict.fromkeys(required_skills)),
        'preferred': list(dict.fromkeys(preferred_skills)),
    }


def compute_text_similarity(text1: str, text2: str) -> float:
    """Simple TF-IDF-like cosine similarity between two texts."""
    def tokenize(text):
        return re.findall(r'\b[a-z][a-z0-9+#.]*\b', text.lower())

    tokens1 = set(tokenize(text1))
    tokens2 = set(tokenize(text2))

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    similarity = len(intersection) / math.sqrt(len(tokens1) * len(tokens2))
    return round(min(similarity * 100 * 3, 100), 1)


def match_resume_to_job(resume_text: str, job_description: str, job_role: str = '') -> Dict[str, Any]:
    """
    Compute job compatibility between resume and job description.
    Returns detailed match analysis.
    """
    resume_skills = extract_skills(resume_text)
    resume_tech = {s.lower() for s in resume_skills['technical']}
    resume_soft = {s.lower() for s in resume_skills['soft']}
    resume_all = resume_tech | resume_soft

    # Get role profile if available
    role_profile = ROLE_PROFILES.get(job_role, None)

    # Extract skills from JD
    jd_skills = extract_job_skills(job_description)
    jd_required = {s.lower() for s in jd_skills['required']}
    jd_preferred = {s.lower() for s in jd_skills['preferred']}

    if role_profile:
        jd_required = jd_required | {s.lower() for s in role_profile['required']}
        jd_preferred = jd_preferred | {s.lower() for s in role_profile['preferred']}

    # If both required and preferred are empty, fall back to general skills in JD
    if not jd_required and not jd_preferred and job_description:
        all_jd_skills = extract_skills(job_description)
        jd_required = {s.lower() for s in all_jd_skills['technical']}
        jd_preferred = {s.lower() for s in all_jd_skills['soft']}

    # Compute matches
    matched_required = resume_all & jd_required
    matched_preferred = resume_all & jd_preferred
    missing_required = jd_required - resume_all
    missing_preferred = jd_preferred - resume_all

    # Skills that partially match (substring or alias)
    partial_matches = []
    for req in list(missing_required):
        for res in resume_all:
            if (req in res or res in req) and req != res:
                partial_matches.append(req)
                missing_required.discard(req)
                break

    # Score calculation
    req_weight = 0.60
    pref_weight = 0.25
    similarity_weight = 0.15

    req_score = (len(matched_required) / max(len(jd_required), 1)) * 100 if jd_required else 60
    pref_score = (len(matched_preferred) / max(len(jd_preferred), 1)) * 100 if jd_preferred else 50
    sim_score = compute_text_similarity(resume_text, job_description)

    overall_match = (
        req_score * req_weight +
        pref_score * pref_weight +
        sim_score * similarity_weight
    )
    overall_match = round(min(overall_match, 100), 1)

    # Skills match percentage
    total_jd_skills = len(jd_required) + len(jd_preferred)
    total_matched = len(matched_required) + len(matched_preferred)
    skills_match_pct = round((total_matched / max(total_jd_skills, 1)) * 100, 1)

    # Format output
    recommendations = generate_match_recommendations(
        overall_match, missing_required, missing_preferred, resume_skills
    )

    return {
        'job_role': job_role or 'Custom Role',
        'overall_match': overall_match,
        'skills_match': skills_match_pct,
        'keywords_match': round(sim_score, 1),
        'experience_match': round(req_score, 1),
        'matched_skills': sorted([s.title() for s in matched_required | matched_preferred]),
        'missing_skills': sorted([s.title() for s in missing_required])[:15],
        'partial_skills': sorted([s.title() for s in partial_matches])[:8],
        'missing_preferred': sorted([s.title() for s in missing_preferred])[:10],
        'recommendations': recommendations,
        'match_breakdown': {
            'required_skills_match': f"{len(matched_required)}/{len(jd_required)}" if jd_required else "N/A",
            'preferred_skills_match': f"{len(matched_preferred)}/{len(jd_preferred)}" if jd_preferred else "N/A",
            'text_similarity': f"{sim_score}%",
        }
    }


def generate_match_recommendations(score: float, missing_req: set, missing_pref: set,
                                    resume_skills: dict) -> List[str]:
    """Generate targeted recommendations to improve job match."""
    recs = []

    if missing_req:
        top_missing = sorted(list(missing_req))[:4]
        recs.append(f"Learn these required skills urgently: {', '.join(s.title() for s in top_missing)}")

    if score < 40:
        recs.append("Your profile has significant gaps for this role — consider building foundational projects before applying.")
    elif score < 60:
        recs.append("Build projects demonstrating the missing required skills to strengthen your application.")
    elif score < 80:
        recs.append("You are a competitive candidate — focus on 2-3 missing skills to become a strong match.")
    else:
        recs.append("Excellent match! Tailor your resume summary and bullet points to emphasize relevant projects and keywords.")

    if missing_pref:
        top_pref = sorted(list(missing_pref))[:3]
        recs.append(f"Nice-to-have skills to learn next: {', '.join(s.title() for s in top_pref)}")

    recs.append("Customize your resume bullet points to mirror exact terminology from this job description.")
    recs.append("Add quantifiable metrics (e.g. 'reduced latency by 35%') for projects involving required technologies.")

    return recs


def compare_multiple_jobs(resume_text: str, job_roles: List[str] = None,
                          custom_roles: List[Dict[str, str]] = None,
                          jobs: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    Compare resume against at least two real job descriptions.
    Requires at least 2 valid job profiles / descriptions.
    Never fabricates results from empty inputs.
    """
    results = []

    # 1. If explicit jobs list provided
    candidate_jobs = []
    if jobs:
        for j in jobs:
            title = j.get('title', '').strip()
            desc = j.get('description', '').strip()
            if title and desc and len(desc) >= 15:
                candidate_jobs.append({'title': title, 'description': desc})

    # 2. If custom_roles provided
    if custom_roles:
        for cr in custom_roles:
            title = cr.get('title', '').strip()
            desc = cr.get('description', '').strip()
            if title and desc and len(desc) >= 15:
                candidate_jobs.append({'title': title, 'description': desc})

    # 3. Preset roles fallback when jobs list is not explicitly provided
    if not jobs and not job_roles:
        job_roles = list(ROLE_PROFILES.keys())

    if job_roles:
        for role in job_roles:
            profile = ROLE_PROFILES.get(role)
            if profile:
                desc = ' '.join(profile['required'] + profile['preferred'] + profile['soft'])
                candidate_jobs.append({'title': role, 'description': desc})

    # Strict validation: Require at least 2 valid job descriptions to compare
    if len(candidate_jobs) < 2:
        raise ValueError("Please provide at least two valid job descriptions for comparison.")

    # Compare each valid job description against the resume
    for c_job in candidate_jobs:
        title = c_job['title']
        desc = c_job['description']
        match = match_resume_to_job(resume_text, desc, title)
        results.append({
            'role': title,
            'match_percentage': match['overall_match'],
            'matched_skills': match['matched_skills'][:8],
            'missing_skills': match['missing_skills'][:6],
            'skills_match': match['skills_match'],
            'top_recommendation': match['recommendations'][0] if match['recommendations'] else '',
            'is_custom': True
        })

    # Sort by match percentage descending
    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    return results
