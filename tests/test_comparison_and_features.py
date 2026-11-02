"""
Test Suite for Multi-Job Comparison, Add & Compare, Compare All Roles,
Job Match, Skill Gap, and Learning Roadmap APIs & Data Structures
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fitz
from app import app, db
from backend.database import User, ResumeUpload, ResumeAnalysis, JobMatch, SkillGap, LearningRoadmap, JobComparison

client = app.test_client()

print("=" * 60)
print("=== VERIFYING COMPARISON, JOB MATCH, SKILL GAP & ROADMAP ===")
print("=" * 60)

# Setup: Register user & upload sample resume
with app.app_context():
    User.query.delete()
    ResumeUpload.query.delete()
    JobComparison.query.delete()
    db.session.commit()

res = client.post('/api/auth/register', json={
    'full_name': 'Dev Tester',
    'email': 'devtester@example.com',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})
assert res.status_code == 201

doc = fitz.open()
page = doc.new_page()
sample_text = """
Dev Tester
Full Stack Software Engineer
devtester@example.com | Seattle, WA

Summary:
Experienced engineer proficient in Python, JavaScript, TypeScript, React, SQL, PostgreSQL, Docker, Git, CI/CD, AWS, and REST APIs.

Experience:
Senior Developer at CloudTech (2020 - Present)
- Designed microservices architecture using Python, FastAPI, Docker, and PostgreSQL.
- Implemented automated CI/CD pipelines and Kubernetes deployment workflows on AWS.
- Built responsive UI components with React and modern CSS.

Education:
B.S. in Computer Science, University of Washington
"""
page.insert_text((50, 72), sample_text)
pdf_bytes = doc.tobytes()
doc.close()

res = client.post('/api/upload-resume', data={
    'file': (io.BytesIO(pdf_bytes), 'dev_tester_resume.pdf')
}, content_type='multipart/form-data')
assert res.status_code == 200
resume_id = res.get_json()['resume_id']
print(f"Uploaded resume ID: {resume_id}")

# 1. Test Resume Analysis
res = client.post('/api/analyze-resume', json={'resume_id': resume_id})
assert res.status_code == 200
analysis_data = res.get_json()
print(f"Analysis completed. Overall Score: {analysis_data['scores']['overall']}")

# 2. Test Compare All Roles (POST /api/compare-jobs)
print("\n--- Testing Compare All Roles (triggerComparison / compareBtn) ---")
res = client.post('/api/compare-jobs', json={'resume_id': resume_id})
assert res.status_code == 200
comp_data = res.get_json()
assert comp_data['success'] is True
assert 'comparisons' in comp_data
assert len(comp_data['comparisons']) > 0
assert 'best_match' in comp_data
assert comp_data['best_match'] is not None
print(f"Total roles compared: {comp_data['total_roles']}")
print(f"Best match role: {comp_data['best_match']['role']} ({comp_data['best_match']['match_percentage']}%)")
for r in comp_data['comparisons'][:4]:
    print(f"  - {r['role']}: {r['match_percentage']}% (Matched: {len(r.get('matched_skills', []))}, Missing: {len(r.get('missing_skills', []))})")

# 3. Test Add & Compare with custom roles (POST /api/compare-jobs with custom_roles)
print("\n--- Testing Add & Compare (addCustomCompBtn) ---")
custom_role = {
    'title': 'AI Cloud Architect',
    'description': 'Requires Python, AWS, Docker, Kubernetes, microservices, FastAPI, and CI/CD.'
}
res = client.post('/api/compare-jobs', json={
    'resume_id': resume_id,
    'custom_roles': [custom_role]
})
assert res.status_code == 200
custom_comp_data = res.get_json()
assert custom_comp_data['success'] is True
found_custom = False
for r in custom_comp_data['comparisons']:
    if r['role'] == 'AI Cloud Architect':
        found_custom = True
        print(f"  ✓ Custom role '{r['role']}' successfully evaluated! Match percentage: {r['match_percentage']}%")
        print(f"    Matched: {r.get('matched_skills')}")
        print(f"    Missing: {r.get('missing_skills')}")
        print(f"    Top Recommendation: {r.get('top_recommendation')}")
assert found_custom, "Custom role 'AI Cloud Architect' should be in comparisons list!"

# 4. Test GET /api/compare-jobs (Initial page load in initComparisonPage)
print("\n--- Testing GET /api/compare-jobs (initComparisonPage Auto-Load) ---")
res = client.get(f'/api/compare-jobs?resume_id={resume_id}')
assert res.status_code == 200
get_comp = res.get_json()
assert get_comp['has_comparison'] is True
assert len(get_comp['comparisons']) > 0
print(f"  ✓ Existing comparison retrieved: {len(get_comp['comparisons'])} roles.")

# 5. Test Job Match (GET and POST /api/job-match)
print("\n--- Testing Job Match Feature ---")
res = client.post('/api/job-match', json={
    'resume_id': resume_id,
    'job_role': 'DevOps Engineer',
    'job_description': 'Seeking AWS, Docker, Kubernetes, CI/CD, Python, and Terraform specialist.'
})
assert res.status_code == 200
jm_data = res.get_json()
assert jm_data['success'] is True
print(f"  ✓ Job match calculated: Overall {jm_data['overall_match']}%, Skills {jm_data['skills_match']}%")

res = client.get(f'/api/job-match?resume_id={resume_id}')
assert res.status_code == 200
assert res.get_json()['has_match'] is True
print("  ✓ GET /api/job-match retrieved saved match.")

# 6. Test Skill Gap (GET and POST /api/skill-gap)
print("\n--- Testing Skill Gap Feature ---")
res = client.post('/api/skill-gap', json={
    'resume_id': resume_id,
    'career_role': 'Software Developer'
})
assert res.status_code == 200
gap_data = res.get_json()
assert gap_data['success'] is True
print(f"  ✓ Skill gap calculated: Overall coverage {gap_data['overall_coverage']}%")

res = client.get(f'/api/skill-gap?resume_id={resume_id}')
assert res.status_code == 200
assert res.get_json()['has_gap'] is True
print("  ✓ GET /api/skill-gap retrieved saved gap analysis.")

# 7. Test Learning Roadmap (GET and POST /api/roadmap, /api/generate-roadmap, /api/roadmap-progress)
print("\n--- Testing Learning Roadmap Feature ---")
res = client.post('/api/generate-roadmap', json={
    'resume_id': resume_id,
    'career_role': 'Software Developer'
})
assert res.status_code == 200
roadmap_data = res.get_json()
assert roadmap_data['success'] is True
roadmap_id = roadmap_data['roadmap_id']
print(f"  ✓ Roadmap generated. Total skills: {roadmap_data['total_skills']}")

res = client.get(f'/api/roadmap?resume_id={resume_id}')
assert res.status_code == 200
assert res.get_json()['has_roadmap'] is True
print("  ✓ GET /api/roadmap retrieved saved roadmap.")

# Test progress toggle
skill_to_complete = roadmap_data['roadmap_items'][0]['skill']
res = client.post('/api/roadmap-progress', json={
    'roadmap_id': roadmap_id,
    'skill_name': skill_to_complete,
    'completed': True
})
assert res.status_code == 200
assert res.get_json()['completed'] is True
assert res.get_json()['completed_items'] >= 1
print(f"  ✓ Marked skill '{skill_to_complete}' completed: progress is {res.get_json()['progress_percentage']}%")

print("\n" + "=" * 60)
print("🎉 ALL COMPARISON, JOB MATCH, SKILL GAP & ROADMAP TESTS PASSED!")
print("=" * 60)
