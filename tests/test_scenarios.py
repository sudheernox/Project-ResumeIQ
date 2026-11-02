import io
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from backend.database import User, ResumeUpload, ResumeAnalysis, JobMatch, SkillGap, LearningRoadmap

client = app.test_client()

# Register and login test user for scenarios
with app.app_context():
    User.query.delete()
    db.session.commit()

client.post('/api/auth/register', json={
    'full_name': 'Scenario Tester',
    'email': 'tester@example.com',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})

print('=== STARTING 13 TEST SCENARIOS ===')

# Scenario 12: Test application with NO uploaded resume
print('\n--- Test Scenario 12: Empty state with no uploaded resume ---')
with app.app_context():
    ResumeUpload.query.delete()
    db.session.commit()

res = client.get('/api/active-resume')
assert res.status_code == 200
data = res.get_json()
assert data['has_resume'] is False
print('GET /api/active-resume -> has_resume: False (PASSED)')

res = client.get('/api/dashboard')
assert res.status_code == 200
assert res.get_json()['has_data'] is False
print('GET /api/dashboard -> has_data: False (PASSED)')

# Scenario 13: Test invalid file uploads and empty inputs
print('\n--- Test Scenario 13: Input validation & error handling ---')
res = client.post('/api/upload-resume', data={'file': (io.BytesIO(b'hello'), 'test.txt')})
assert res.status_code == 400
print('POST /api/upload-resume with .txt -> 400 Bad Request (PASSED)')

res = client.post('/api/upload-resume', data={})
assert res.status_code == 400
print('POST /api/upload-resume empty file -> 400 Bad Request (PASSED)')

res = client.post('/api/job-match', json={'job_role': '', 'job_description': ''})
assert res.status_code == 400
print('POST /api/job-match empty inputs -> 400 Bad Request (PASSED)')

# Scenario 1: Upload a PDF resume
print('\n--- Test Scenario 1: Upload a PDF resume ---')
import fitz
doc = fitz.open()
page = doc.new_page()
sample_text = """
Alex Rivera
Full Stack Software Engineer
alex.rivera@example.com | +1 (555) 234-5678 | linkedin.com/in/alexrivera | github.com/alexrivera

Education:
B.S. in Computer Science, University of Technology, 2019 - 2023

Skills:
Python, JavaScript, TypeScript, React, Node.js, Express, SQL, PostgreSQL, Docker, Git, REST, HTML5, CSS3, Tailwind, Problem Solving, Communication, Teamwork

Experience:
Software Engineer at CloudCorp (2023 - Present)
• Developed 20+ RESTful APIs using Python and FastAPI, reducing request latency by 35%
• Implemented responsive web application frontends with React and Tailwind CSS
• Optimized PostgreSQL queries and database schemas for high-traffic microservices

Projects:
AI Document Search Platform (Python, React, Docker, PostgreSQL)
• Built an end-to-end full stack search engine containerized with Docker
• Integrated full-text indexing and REST endpoints for document querying
"""
page.insert_text((50, 50), sample_text)
pdf_bytes = doc.write()
doc.close()

res = client.post('/api/upload-resume', data={'file': (io.BytesIO(pdf_bytes), 'Alex_Rivera_Resume.pdf')})
assert res.status_code == 200
upload_data = res.get_json()
resume_id = upload_data['resume_id']
assert upload_data['success'] is True
print(f"Uploaded resume ID: {resume_id}, filename: {upload_data['filename']} (PASSED)")

# Scenario 2: Analyze the uploaded resume
print('\n--- Test Scenario 2: Analyze uploaded resume ---')
res = client.post('/api/analyze-resume', json={'resume_id': resume_id})
assert res.status_code == 200
analysis_data = res.get_json()
assert analysis_data['success'] is True
scores = analysis_data['scores']
print('Calculated Scores:', scores)
assert scores['overall'] > 0
print(f"Skills extracted: {analysis_data['technical_skills']} (PASSED)")

# Scenario 3 & 4: Persistence across pages and browser refresh
print('\n--- Test Scenario 3 & 4: Data persistence across navigation & refresh ---')
res = client.get('/api/active-resume')
assert res.status_code == 200
active_data = res.get_json()
assert active_data['has_resume'] is True
assert active_data['resume']['id'] == resume_id
assert active_data['analysis'] is not None
assert active_data['analysis']['scores']['overall'] == scores['overall']
print('Active resume maintained with full analysis on simulated reload (PASSED)')

res = client.get('/api/dashboard')
dash_data = res.get_json()
assert dash_data['has_data'] is True
assert dash_data['summary']['overall_score'] == scores['overall']
print('GET /api/dashboard retrieves active resume analysis (PASSED)')

# Scenario 5: Job Match with a real job description
print('\n--- Test Scenario 5: Job Match calculation ---')
job_desc = """
Senior Backend Engineer
Requirements:
- 3+ years experience with Python, FastAPI or Flask
- Strong knowledge of SQL, PostgreSQL, Docker, and AWS
- Experience with Kubernetes and microservices
- Preferred: React, Redis, CI/CD, Problem Solving
"""
res = client.post('/api/job-match', json={
    'job_role': 'Software Developer',
    'job_description': job_desc
})
assert res.status_code == 200
match_data = res.get_json()
assert match_data['success'] is True
print(f"Job Match Overall: {match_data['overall_match']}%, Skills Match: {match_data['skills_match']}%")
print(f"Matched skills: {match_data['matched_skills']}")
print(f"Missing skills: {match_data['missing_skills']}")
assert len(match_data['matched_skills']) > 0

res_get_match = client.get('/api/job-match')
assert res_get_match.status_code == 200
assert res_get_match.get_json()['has_match'] is True
print('Saved job match retrieved on reload (PASSED)')

# Scenario 6: Skill Gap Analysis
print('\n--- Test Scenario 6: Skill Gap Analysis ---')
res = client.post('/api/skill-gap', json={'career_role': 'Software Developer'})
assert res.status_code == 200
gap_data = res.get_json()
assert gap_data['success'] is True
assert 'radar_data' in gap_data
print(f"Software Developer Skill Coverage: {gap_data['overall_coverage']}%, Missing Tech: {gap_data['missing_technical']}")
res_get_gap = client.get('/api/skill-gap?career_role=Software Developer')
assert res_get_gap.status_code == 200
assert res_get_gap.get_json()['has_gap'] is True
print('Saved skill gap retrieved on reload (PASSED)')

# Scenario 7: Personalized Learning Roadmap
print('\n--- Test Scenario 7: Generate Learning Roadmap ---')
res = client.post('/api/generate-roadmap', json={'career_role': 'Software Developer'})
assert res.status_code == 200
roadmap_data = res.get_json()
roadmap_id = roadmap_data['roadmap_id']
items = roadmap_data['roadmap_items']
assert len(items) > 0
print(f"Roadmap generated with {len(items)} skills. Stages: {list(items[0]['stages'].keys())}")
assert set(items[0]['stages'].keys()) == {'learn', 'practice', 'build', 'apply'}
print('4 stages (Learn, Practice, Build, Apply) verified (PASSED)')

# Scenario 8 & 9: Mark roadmap task complete and verify persistence after refresh
print('\n--- Test Scenario 8 & 9: Roadmap progress persistence ---')
first_skill = items[0]['skill']
res = client.post('/api/roadmap-progress', json={
    'roadmap_id': roadmap_id,
    'skill_name': first_skill,
    'completed': True
})
assert res.status_code == 200
prog_data = res.get_json()
assert prog_data['completed'] is True
assert prog_data['completed_items'] >= 1
print(f"Marked {first_skill} completed. Progress: {prog_data['progress_percentage']}%")

# Simulate page refresh by calling GET /api/roadmap
res_reload = client.get('/api/roadmap?career_role=Software Developer')
assert res_reload.status_code == 200
reloaded = res_reload.get_json()
assert reloaded['has_roadmap'] is True
assert reloaded['completed_items'] >= 1
reloaded_item = [i for i in reloaded['roadmap_items'] if i['skill'].lower() == first_skill.lower()][0]
assert reloaded_item['completed'] is True
print(f"Roadmap progress preserved after reload: {reloaded['progress_percentage']}% (PASSED)")

# Scenario 10 & 11: Multi-Job Comparison with genuine calculations & custom role
print('\n--- Test Scenario 10 & 11: Multi-Job Comparison ---')
res = client.post('/api/compare-jobs', json={
    'custom_roles': [{'title': 'Custom Cloud Architect', 'description': 'Python, AWS, Docker, Microservices, PostgreSQL, SQL'}]
})
assert res.status_code == 200
comp_data = res.get_json()
assert comp_data['success'] is True
comparisons = comp_data['comparisons']
assert len(comparisons) >= 5
print(f"Compared {len(comparisons)} roles. Best Match: {comp_data['best_match']['role']} ({comp_data['best_match']['match_percentage']}%)")
for c in comparisons:
    print(f" - {c['role']}: {c['match_percentage']}%")

res_get_comp = client.get('/api/compare-jobs')
assert res_get_comp.status_code == 200
assert res_get_comp.get_json()['has_comparison'] is True
print('Saved comparison retrieved on reload (PASSED)')

# Test Switching Resumes and Deleting Resume
print('\n--- Testing Multiple Resumes Switching & Deletion ---')
doc2 = fitz.open()
page2 = doc2.new_page()
page2.insert_text((50, 50), "Jane Smith\nData Analyst\njane@example.com\nSkills: Python, SQL, Tableau, Excel, Pandas, Statistics")
pdf_bytes2 = doc2.write()
doc2.close()

res2 = client.post('/api/upload-resume', data={'file': (io.BytesIO(pdf_bytes2), 'Jane_Smith_Resume.pdf')})
res2_id = res2.get_json()['resume_id']

res_list = client.get('/api/resumes')
assert res_list.get_json()['total'] == 2
print(f"2 resumes listed. Active ID: {res_list.get_json()['active_id']}")

# Switch back to first resume
res_switch = client.post('/api/set-active-resume', json={'resume_id': resume_id})
assert res_switch.status_code == 200
assert res_switch.get_json()['resume']['id'] == resume_id
print('Switched active resume back to first resume (PASSED)')

# Delete second resume
res_del = client.delete(f'/api/delete-resume/{res2_id}')
assert res_del.status_code == 200
assert res_del.get_json()['success'] is True
print('Deleted second resume (PASSED)')

print('\n=== ALL 13 TEST SCENARIOS PASSED WITH ZERO ERRORS! ===')
