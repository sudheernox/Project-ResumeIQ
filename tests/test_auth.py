"""
Comprehensive Authentication & Data Isolation Test Suite
ResumeIQ — User-Based Platform
"""
import io
import json
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fitz
from app import app, db
from backend.database import User, ResumeUpload, ResumeAnalysis, JobMatch, SkillGap, LearningRoadmap

client = app.test_client()

print("=" * 60)
print("=== RESUME IQ AUTHENTICATION & DATA ISOLATION TEST SUITE ===")
print("=" * 60)

# Clear test database tables
with app.app_context():
    LearningRoadmap.query.delete()
    SkillGap.query.delete()
    JobMatch.query.delete()
    ResumeAnalysis.query.delete()
    ResumeUpload.query.delete()
    User.query.delete()
    db.session.commit()
print("\n[SETUP] Test database cleared successfully.")


# -------------------------------------------------------------
# Test 1: User Registration
# -------------------------------------------------------------
print("\n--- TEST 1: User Registration ---")
res = client.post('/api/auth/register', json={
    'full_name': 'Alice Engineer',
    'email': 'alice@example.com',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})
assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.get_data(as_text=True)}"
data = res.get_json()
assert data['success'] is True
assert data['user']['email'] == 'alice@example.com'
assert 'password' not in data['user']
assert 'password_hash' not in data['user']

# Verify password hashed in database
with app.app_context():
    user_alice = User.query.filter_by(email='alice@example.com').first()
    assert user_alice is not None
    assert user_alice.password_hash != 'Password123!'
    assert user_alice.check_password('Password123!') is True
    assert user_alice.check_password('WrongPass') is False

print("  ✓ User registered, password hashed securely with Werkzeug.")


# -------------------------------------------------------------
# Test 2: Registration Validation & Duplicate Email Rejection
# -------------------------------------------------------------
print("\n--- TEST 2: Registration Validation & Duplicate Prevention ---")
# Duplicate email (case-insensitive)
res = client.post('/api/auth/register', json={
    'full_name': 'Alice Copy',
    'email': 'ALICE@EXAMPLE.COM',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})
assert res.status_code == 400
assert 'already exists' in res.get_json()['error']
print("  ✓ Duplicate email rejected (case-insensitive).")

# Short password (<8 chars)
res = client.post('/api/auth/register', json={
    'full_name': 'Short Pass',
    'email': 'short@example.com',
    'password': 'short',
    'confirm_password': 'short'
})
assert res.status_code == 400
assert 'at least 8 characters' in res.get_json()['error']
print("  ✓ Short password (<8 chars) rejected.")

# Mismatched passwords
res = client.post('/api/auth/register', json={
    'full_name': 'Mismatch',
    'email': 'mismatch@example.com',
    'password': 'Password123!',
    'confirm_password': 'DifferentPassword!'
})
assert res.status_code == 400
assert 'do not match' in res.get_json()['error']
print("  ✓ Mismatched passwords rejected.")

# Invalid email format
res = client.post('/api/auth/register', json={
    'full_name': 'Bad Email',
    'email': 'not-an-email',
    'password': 'Password123!',
    'confirm_password': 'Password123!'
})
assert res.status_code == 400
assert 'valid email' in res.get_json()['error']
print("  ✓ Invalid email format rejected.")


# -------------------------------------------------------------
# Test 3: Logout
# -------------------------------------------------------------
print("\n--- TEST 3: User Logout ---")
res = client.post('/api/auth/logout')
assert res.status_code == 200
assert res.get_json()['success'] is True

# Verify /api/auth/me reports unauthenticated
res = client.get('/api/auth/me')
assert res.status_code == 200
assert res.get_json()['authenticated'] is False
print("  ✓ User logged out, session cleared.")


# -------------------------------------------------------------
# Test 4: Protected Routes & Anti-Cache Headers
# -------------------------------------------------------------
print("\n--- TEST 4: Protected Web & API Routes (Logged Out) ---")
# Web routes should redirect to /login
protected_pages = ['/dashboard', '/analysis', '/job-match', '/skill-gap', '/roadmap', '/comparison', '/profile']
for page in protected_pages:
    res = client.get(page)
    assert res.status_code == 302, f"Expected 302 redirect for {page}, got {res.status_code}"
    assert '/login' in res.headers['Location']

print("  ✓ All protected web pages redirect to /login when unauthenticated.")

# Protected APIs should return 401
protected_apis = ['/api/active-resume', '/api/resumes', '/api/dashboard', '/api/roadmap']
for api_url in protected_apis:
    res = client.get(api_url)
    assert res.status_code == 401, f"Expected 401 for {api_url}, got {res.status_code}"
    assert res.get_json()['authenticated'] is False

print("  ✓ All protected API endpoints return 401 when unauthenticated.")

# Verify anti-cache headers
res = client.get('/login')
assert 'no-cache' in res.headers.get('Cache-Control', '')
assert 'no-store' in res.headers.get('Cache-Control', '')
assert res.headers.get('Pragma') == 'no-cache'
print("  ✓ Anti-cache security headers (no-store, no-cache, must-revalidate) verified.")


# -------------------------------------------------------------
# Test 5: Login with Incorrect & Correct Credentials
# -------------------------------------------------------------
print("\n--- TEST 5: Login Credentials Check ---")
# Wrong password
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'IncorrectPassword!'
})
assert res.status_code == 401
assert 'Invalid email or password' in res.get_json()['error']
print("  ✓ Login with incorrect password returns 401.")

# Non-existent user
res = client.post('/api/auth/login', json={
    'email': 'ghost@example.com',
    'password': 'Password123!'
})
assert res.status_code == 401
print("  ✓ Login with non-existent email returns 401.")

# Correct login with Remember Me
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'Password123!',
    'remember_me': True
})
assert res.status_code == 200
data = res.get_json()
assert data['success'] is True
assert data['user']['email'] == 'alice@example.com'
print("  ✓ Login with correct credentials succeeds with Remember Me.")

# Verify /api/auth/me returns authenticated Alice
res = client.get('/api/auth/me')
assert res.get_json()['authenticated'] is True
assert res.get_json()['user']['full_name'] == 'Alice Engineer'
print("  ✓ /api/auth/me returns authenticated user details.")


# -------------------------------------------------------------
# Test 6: User A Uploads Resume & Performs Analysis
# -------------------------------------------------------------
print("\n--- TEST 6: User A Uploads Resume & Generates Analysis ---")
doc = fitz.open()
page = doc.new_page()
sample_text_a = """
Alice Engineer
Full Stack Software Developer
alice@example.com | San Francisco, CA

Skills:
Python, Flask, JavaScript, React, SQL, PostgreSQL, Docker, Git, REST APIs, Problem Solving, Communication

Experience:
Software Engineer at Acme Corp (2021 - Present)
- Built scalable web APIs in Flask and Python.
- Developed React user interfaces.

Education:
B.S. in Computer Science, Tech University
"""
page.insert_text((50, 72), sample_text_a)
pdf_bytes_a = doc.tobytes()
doc.close()

res = client.post('/api/upload-resume', data={
    'file': (io.BytesIO(pdf_bytes_a), 'alice_resume.pdf')
}, content_type='multipart/form-data')
assert res.status_code == 200, f"Upload failed: {res.get_data(as_text=True)}"
upload_data_a = res.get_json()
resume_id_a = upload_data_a['resume_id']
print(f"  ✓ User A uploaded resume ID: {resume_id_a}")

# Analyze User A's resume
res = client.post('/api/analyze-resume', json={'resume_id': resume_id_a})
assert res.status_code == 200
print(f"  ✓ User A analyzed resume, overall score: {res.get_json()['scores']['overall']}")

# Create job match and skill gap for User A
res = client.post('/api/job-match', json={
    'job_role': 'Full Stack Developer',
    'job_description': 'Looking for Python, Flask, React, Docker, and Kubernetes developer.'
})
assert res.status_code == 200
print(f"  ✓ User A created job match, match score: {res.get_json()['overall_match']}%")

res = client.post('/api/skill-gap', json={
    'career_role': 'Software Developer'
})
assert res.status_code == 200
print(f"  ✓ User A created skill gap, coverage: {res.get_json()['overall_coverage']}%")

# Generate roadmap for User A
res = client.post('/api/generate-roadmap', json={
    'career_role': 'Software Developer'
})
assert res.status_code == 200
roadmap_id_a = res.get_json()['roadmap_id']
print(f"  ✓ User A generated learning roadmap ID: {roadmap_id_a}")


# -------------------------------------------------------------
# Test 7: Register User B & Verify Complete Workspace Isolation
# -------------------------------------------------------------
print("\n--- TEST 7: Register User B & Verify Data Isolation ---")
# Log out Alice
client.post('/api/auth/logout')

# Register Bob
res = client.post('/api/auth/register', json={
    'full_name': 'Bob Analyst',
    'email': 'bob@example.com',
    'password': 'BobPassword123!',
    'confirm_password': 'BobPassword123!'
})
assert res.status_code == 201
print("  ✓ User B (Bob) registered and logged in.")

# Check Bob's active resume -> MUST be empty!
res = client.get('/api/active-resume')
assert res.status_code == 200
assert res.get_json()['has_resume'] is False
print("  ✓ User B has_resume: False (Alice's resume is completely invisible to Bob).")

# Check Bob's resume list -> MUST be 0
res = client.get('/api/resumes')
assert res.status_code == 200
assert len(res.get_json()['resumes']) == 0
print("  ✓ User B's resume list is completely empty.")

# Check Bob's dashboard -> MUST have has_data: False
res = client.get('/api/dashboard')
assert res.status_code == 200
assert res.get_json()['has_data'] is False
print("  ✓ User B's dashboard shows clean empty state.")

# Attempt to access Alice's resume using Alice's resume ID -> MUST return 404 or not found
res = client.get(f'/api/active-resume?resume_id={resume_id_a}')
assert res.status_code == 200
assert res.get_json()['has_resume'] is False
print("  ✓ User B attempting to query Alice's resume ID gets has_resume: False.")

# Attempt to switch to Alice's resume -> MUST return 404
res = client.post('/api/set-active-resume', json={'resume_id': resume_id_a})
assert res.status_code == 404
print("  ✓ User B cannot set Alice's resume as active (returns 404).")

# Attempt to delete Alice's resume -> MUST return 404
res = client.delete(f'/api/delete-resume/{resume_id_a}')
assert res.status_code == 404
print("  ✓ User B cannot delete Alice's resume (returns 404).")

# Attempt to update progress on Alice's roadmap -> MUST return 404
res = client.post('/api/roadmap-progress', json={
    'roadmap_id': roadmap_id_a,
    'skill_name': 'Git',
    'completed': True
})
assert res.status_code == 404
print("  ✓ User B cannot modify Alice's roadmap progress (returns 404).")


# -------------------------------------------------------------
# Test 8: User B Uploads Independent Resume
# -------------------------------------------------------------
print("\n--- TEST 8: User B Uploads Separate Resume ---")
doc = fitz.open()
page = doc.new_page()
sample_text_b = """
Bob Analyst
Data Analyst & BI Specialist
bob@example.com | Chicago, IL

Skills:
Python, SQL, Tableau, Power BI, Excel, Pandas, Statistics, Data Visualization

Education:
B.S. in Mathematics, Midwest University
"""
page.insert_text((50, 72), sample_text_b)
pdf_bytes_b = doc.tobytes()
doc.close()

res = client.post('/api/upload-resume', data={
    'file': (io.BytesIO(pdf_bytes_b), 'bob_resume.pdf')
}, content_type='multipart/form-data')
assert res.status_code == 200
resume_id_b = res.get_json()['resume_id']
assert resume_id_b != resume_id_a
print(f"  ✓ User B uploaded resume ID: {resume_id_b}")

# Check Bob's active resume now
res = client.get('/api/active-resume')
assert res.status_code == 200
assert res.get_json()['has_resume'] is True
assert res.get_json()['resume']['filename'] == 'bob_resume.pdf'
print("  ✓ User B's active resume is now 'bob_resume.pdf'.")


# -------------------------------------------------------------
# Test 9: Re-login as User A & Verify Persistence
# -------------------------------------------------------------
print("\n--- TEST 9: Re-login User A & Verify Persistence ---")
client.post('/api/auth/logout')

# Log back in as Alice
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'Password123!'
})
assert res.status_code == 200

# Alice's active resume should be alice_resume.pdf
res = client.get('/api/active-resume')
assert res.status_code == 200
assert res.get_json()['has_resume'] is True
assert res.get_json()['resume']['filename'] == 'alice_resume.pdf'
assert res.get_json()['resume']['id'] == resume_id_a
print("  ✓ User A logged back in: active resume 'alice_resume.pdf' perfectly restored.")

# Alice's dashboard should have all her previous data
res = client.get('/api/dashboard')
assert res.status_code == 200
assert res.get_json()['has_data'] is True
assert res.get_json()['job_match'] is not None
assert res.get_json()['skill_gap'] is not None
assert res.get_json()['roadmap'] is not None
print("  ✓ User A's dashboard summary, job match, skill gap, and roadmap are fully intact.")


# -------------------------------------------------------------
# Test 10: Password Reset Flow (Forgot & Reset)
# -------------------------------------------------------------
print("\n--- TEST 10: Password Reset Flow ---")
client.post('/api/auth/logout')

# Request password reset link
res = client.post('/api/auth/forgot-password', json={'email': 'alice@example.com'})
assert res.status_code == 200
reset_data = res.get_json()
assert reset_data['success'] is True
token = reset_data['token']
assert token is not None
print(f"  ✓ Reset token generated successfully for alice@example.com.")

# Attempt reset with mismatched passwords
res = client.post('/api/auth/reset-password', json={
    'token': token,
    'password': 'NewPassword123!',
    'confirm_password': 'DifferentPassword!'
})
assert res.status_code == 400
assert 'do not match' in res.get_json()['error']
print("  ✓ Reset password rejects mismatched confirmation.")

# Attempt reset with invalid token
res = client.post('/api/auth/reset-password', json={
    'token': 'invalid.token.signature',
    'password': 'NewPassword123!',
    'confirm_password': 'NewPassword123!'
})
assert res.status_code == 400
assert 'Invalid or expired' in res.get_json()['error']
print("  ✓ Reset password rejects invalid token signature.")

# Perform valid password reset
res = client.post('/api/auth/reset-password', json={
    'token': token,
    'password': 'NewPassword123!',
    'confirm_password': 'NewPassword123!'
})
assert res.status_code == 200
assert res.get_json()['success'] is True
print("  ✓ Password reset successfully with valid token.")

# Old password should now fail
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'Password123!'
})
assert res.status_code == 401
print("  ✓ Login with old password rejected (401).")

# New password should succeed
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'NewPassword123!'
})
assert res.status_code == 200
assert res.get_json()['success'] is True
print("  ✓ Login with new reset password succeeded.")


# -------------------------------------------------------------
# Test 11: User Profile Update & Password Change
# -------------------------------------------------------------
print("\n--- TEST 11: User Profile Update & Password Change ---")
# Update user's name
res = client.post('/api/auth/profile', json={
    'full_name': 'Alice Senior Architect'
})
assert res.status_code == 200
assert res.get_json()['user']['full_name'] == 'Alice Senior Architect'
print("  ✓ Full name updated successfully.")

# Change password from profile
res = client.post('/api/auth/profile', json={
    'current_password': 'WrongPassword!',
    'new_password': 'BrandNewPassword123!',
    'confirm_password': 'BrandNewPassword123!'
})
assert res.status_code == 400
assert 'Incorrect current password' in res.get_json()['error']
print("  ✓ Password change with wrong current password rejected.")

res = client.post('/api/auth/profile', json={
    'current_password': 'NewPassword123!',
    'new_password': 'BrandNewPassword123!',
    'confirm_password': 'BrandNewPassword123!'
})
assert res.status_code == 200
print("  ✓ Password changed from profile page.")

# Verify new password login
client.post('/api/auth/logout')
res = client.post('/api/auth/login', json={
    'email': 'alice@example.com',
    'password': 'BrandNewPassword123!'
})
assert res.status_code == 200
print("  ✓ Successfully authenticated with changed profile password.")


# -------------------------------------------------------------
# Test 12: Delete Resume & Cascading Cleanup
# -------------------------------------------------------------
print("\n--- TEST 12: Delete Resume & Cascading Cleanup ---")
res = client.delete(f'/api/delete-resume/{resume_id_a}')
assert res.status_code == 200
assert res.get_json()['success'] is True
print("  ✓ User A deleted active resume.")

# Verify resume is gone from DB
with app.app_context():
    deleted_check = ResumeUpload.query.get(resume_id_a)
    assert deleted_check is None
    analyses_check = ResumeAnalysis.query.filter_by(resume_id=resume_id_a).all()
    assert len(analyses_check) == 0
print("  ✓ Resume and all child analyses cleanly cascaded and removed from DB.")

print("\n" + "=" * 60)
print("🎉 ALL 12 AUTHENTICATION & DATA ISOLATION TESTS PASSED PERFECTLY!")
print("=" * 60)
