import os
import sys
import unittest
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from backend.database import User, ResumeUpload, ResumeAnalysis, JobMatch, LearningRoadmap, RoadmapProgress
from backend.resume_analyzer import score_resume, analyze_resume
from backend.email_service import send_password_reset_email


class TestFullPlatformFeatures(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def create_user_and_login(self, email='tester@example.com', password='Password123!', full_name='Test User'):
        res = self.app.post('/api/auth/register', json={
            'full_name': full_name,
            'email': email,
            'password': password,
            'confirm_password': password
        })
        self.assertIn(res.status_code, [200, 201])
        return res

    # --------------------------------------------------------------------------
    # Scenario 1: Realistic ATS score for good resume (never 100%)
    # --------------------------------------------------------------------------
    def test_realistic_ats_score_good_resume(self):
        good_parsed = {
            'name': 'Alex Johnson',
            'email': 'alex@example.com',
            'phone': '+1 555-019-2834',
            'linkedin': 'https://linkedin.com/in/alexjohnson',
            'github': 'https://github.com/alexjohnson',
            'word_count': 500,
            'raw_text': """
Alex Johnson
Email: alex@example.com | Phone: +1 555-019-2834 | LinkedIn: https://linkedin.com/in/alexjohnson | GitHub: https://github.com/alexjohnson

PROFESSIONAL SUMMARY
Experienced Senior Full Stack Developer with 5+ years building distributed Python and TypeScript applications.

SKILLS
Python, Flask, Django, PostgreSQL, Docker, Kubernetes, AWS, React, TypeScript, Git, REST APIs, Microservices, CI/CD, Redis.

WORK EXPERIENCE
Senior Software Engineer - CloudScale Inc (2021 - Present)
- Engineered high-throughput REST APIs handling 4.5 million daily requests with 99.98% uptime.
- Optimized PostgreSQL queries cutting database latency by 42%.
- Architected CI/CD deployment pipelines using Docker and Kubernetes.

Software Engineer - TechForward (2019 - 2021)
- Developed responsive web interfaces using React and TypeScript.
- Integrated payment gateways processing $2.5M in monthly transactions.

EDUCATION
Bachelor of Science in Computer Science - State University (2015 - 2019)
GPA: 3.8 / 4.0

PROJECTS
- Distributed Task Orchestrator: Built task queue system in Python and Redis supporting 10,000 tasks/min.
- Cloud Metrics Dashboard: Real-time monitoring platform using Docker, Prometheus and React.
""",
            'sections': {
                'skills': 'Python, Flask, Django, PostgreSQL, Docker, AWS, React',
                'experience': 'Senior Software Engineer - CloudScale Inc... Software Engineer - TechForward...',
                'education': 'Bachelor of Science in Computer Science - State University (2015 - 2019)',
                'projects': 'Distributed Task Orchestrator, Cloud Metrics Dashboard',
                'summary': 'Experienced Senior Full Stack Developer...'
            },
            'technical_skills': ['Python', 'Flask', 'Django', 'PostgreSQL', 'Docker', 'Kubernetes', 'AWS', 'React', 'TypeScript', 'Git', 'REST APIs', 'Microservices', 'CI/CD', 'Redis'],
            'soft_skills': ['Leadership', 'Problem Solving', 'Communication', 'Collaboration'],
            'education': [{'degree': 'Bachelor of Science', 'institution': 'State University', 'year': '2019'}],
            'experience': [{'role': 'Senior Software Engineer', 'company': 'CloudScale Inc', 'duration': '2021 - Present', 'highlights': ['Engineered high-throughput REST APIs handling 4.5 million daily requests.']}],
            'projects': [{'title': 'Distributed Task Orchestrator', 'technologies': ['Python', 'Redis']}],
            'certifications': []
        }

        result = analyze_resume(good_parsed)
        scores = result['scores']
        deductions = result['deductions_summary']
        category_scores = result['category_scores']
        ats_disclaimer = result['ats_disclaimer']
        
        # Must never automatically give 100%
        self.assertLessEqual(scores['overall'], 93.5, "Overall score must be capped at 93.5% realistic ceiling")
        self.assertGreaterEqual(scores['overall'], 70.0, "Solid resume should score reasonably high")
        self.assertIn('skills_relevance', category_scores)
        self.assertIn('experience_achievements', category_scores)
        self.assertIn('formatting_structure', category_scores)
        self.assertIn('education_projects', category_scores)
        self.assertIn('ats_compatibility', category_scores)
        self.assertIn('contact_completeness', category_scores)
        self.assertTrue(len(ats_disclaimer) > 20)

    # --------------------------------------------------------------------------
    # Scenario 2: Badly formatted / sparse resume receives appropriately lower score
    # --------------------------------------------------------------------------
    def test_badly_formatted_resume_receives_low_score(self):
        bad_parsed = {
            'name': 'Unknown',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'word_count': 35,
            'raw_text': "I want a job. Skills: java. Worked at a store for 2 months.",
            'sections': {},
            'technical_skills': ['Java'],
            'soft_skills': [],
            'education': [],
            'experience': [],
            'projects': [],
            'certifications': []
        }

        result = analyze_resume(bad_parsed)
        scores = result['scores']
        deductions = result['deductions_summary']
        suggestions = result['recommendations']
        
        # Badly formatted sparse resume should score under 40%
        self.assertLess(scores['overall'], 40.0, f"Sparse/bad resume score should be low, got {scores['overall']}")
        self.assertTrue(len(deductions) >= 3, "Sparse/bad resume must produce multiple deduction items")
        self.assertTrue(len(suggestions) >= 2, "Sparse/bad resume must produce actionable improvement suggestions")

    # --------------------------------------------------------------------------
    # Scenario 3: Job Match without JD returns 400 validation error
    # --------------------------------------------------------------------------
    def test_job_match_without_jd_rejected(self):
        self.create_user_and_login()
        
        with app.app_context():
            user = User.query.filter_by(email='tester@example.com').first()
            upload = ResumeUpload(
                user_id=user.id,
                filename='test.pdf',
                original_filename='test.pdf',
                file_path='test.pdf',
                file_size=1024,
                is_active=True
            )
            db.session.add(upload)
            db.session.commit()
            resume_id = upload.id

        # Post with empty job description
        res = self.app.post('/api/job-match', json={
            'resume_id': resume_id,
            'job_role': 'Software Developer',
            'job_description': ''
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn('Please upload or paste a job description', data.get('error', ''))

        # Post with too short job description (< 15 chars)
        res_short = self.app.post('/api/job-match', json={
            'resume_id': resume_id,
            'job_role': 'Software Developer',
            'job_description': 'short jd'
        })
        self.assertEqual(res_short.status_code, 400)

    # --------------------------------------------------------------------------
    # Scenario 4: Job Match with valid JD computes genuine match
    # --------------------------------------------------------------------------
    def test_job_match_with_valid_jd(self):
        self.create_user_and_login()
        
        with app.app_context():
            user = User.query.filter_by(email='tester@example.com').first()
            upload = ResumeUpload(
                user_id=user.id,
                filename='test.pdf',
                original_filename='test.pdf',
                file_path='test.pdf',
                text_content='Python, Flask, PostgreSQL, Docker, Git, REST APIs',
                file_size=1024,
                is_active=True
            )
            db.session.add(upload)
            db.session.commit()

            analysis = ResumeAnalysis(
                user_id=user.id,
                resume_id=upload.id,
                overall_score=85,
                skills_score=85,
                technical_skills=json.dumps(['Python', 'Flask', 'PostgreSQL', 'Docker']),
                soft_skills=json.dumps(['Communication'])
            )
            db.session.add(analysis)
            db.session.commit()
            resume_id = upload.id

        res = self.app.post('/api/job-match', json={
            'resume_id': resume_id,
            'job_role': 'Python Backend Engineer',
            'job_description': 'We require a Python Backend Engineer with experience in Flask, PostgreSQL, Docker, and Kubernetes.'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('overall_match', data)
        self.assertIn('matched_skills', data)
        self.assertIn('Python', data['matched_skills'])
        self.assertIn('Flask', data['matched_skills'])

    # --------------------------------------------------------------------------
    # Scenario 5: Learning Roadmap requires valid JD / skill gaps
    # --------------------------------------------------------------------------
    def test_roadmap_requires_valid_data(self):
        self.create_user_and_login()
        
        with app.app_context():
            user = User.query.filter_by(email='tester@example.com').first()
            upload = ResumeUpload(
                user_id=user.id,
                filename='test.pdf',
                original_filename='test.pdf',
                file_path='test.pdf',
                file_size=1024,
                is_active=True
            )
            db.session.add(upload)
            db.session.commit()
            resume_id = upload.id

        # Generating roadmap without any skills, JD or prior analysis returns 400
        res = self.app.post('/api/generate-roadmap', json={
            'resume_id': resume_id,
            'career_role': '',
            'missing_skills': []
        })
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn('job description', data.get('error', '').lower())

    # --------------------------------------------------------------------------
    # Scenario 6: Job Comparison requires at least 2 valid JDs
    # --------------------------------------------------------------------------
    def test_comparison_requires_at_least_two_jobs(self):
        self.create_user_and_login()
        
        with app.app_context():
            user = User.query.filter_by(email='tester@example.com').first()
            upload = ResumeUpload(
                user_id=user.id,
                filename='test.pdf',
                original_filename='test.pdf',
                file_path='test.pdf',
                file_size=1024,
                is_active=True
            )
            db.session.add(upload)
            db.session.commit()

            analysis = ResumeAnalysis(
                user_id=user.id,
                resume_id=upload.id,
                overall_score=85,
                technical_skills=json.dumps(['Python', 'Flask', 'SQL']),
                soft_skills=json.dumps([])
            )
            db.session.add(analysis)
            db.session.commit()
            resume_id = upload.id

        # Only 1 job provided
        res_single = self.app.post('/api/compare-jobs', json={
            'resume_id': resume_id,
            'jobs': [
                {'title': 'Job 1', 'description': 'Python Flask Developer needed with SQL skills'}
            ]
        })
        self.assertEqual(res_single.status_code, 400)
        data = json.loads(res_single.data)
        self.assertIn('at least two', data.get('error', '').lower())

        # 2 valid jobs provided
        res_double = self.app.post('/api/compare-jobs', json={
            'resume_id': resume_id,
            'jobs': [
                {'title': 'Job 1', 'description': 'Python Flask Developer needed with SQL and Docker.'},
                {'title': 'Job 2', 'description': 'Full Stack Developer with React, Node.js, and TypeScript.'}
            ]
        })
        self.assertEqual(res_double.status_code, 200)
        comp_data = json.loads(res_double.data)
        self.assertEqual(len(comp_data['comparisons']), 2)
        self.assertIn('best_match', comp_data)

    # --------------------------------------------------------------------------
    # Scenario 7: Forgot password and Gmail email service diagnostics
    # --------------------------------------------------------------------------
    def test_forgot_password_diagnostics(self):
        self.create_user_and_login(email='forgotuser@example.com')
        
        # Request password reset for existing email
        res = self.app.post('/api/auth/forgot-password', json={
            'email': 'forgotuser@example.com'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get('success'))
        # Should provide dev token or notice when SMTP is unconfigured in test environment
        self.assertTrue('notice' in data or data.get('email_sent') is True)

    # --------------------------------------------------------------------------
    # Scenario 8: User isolation (User A cannot access User B's data)
    # --------------------------------------------------------------------------
    def test_user_data_isolation(self):
        # Register User A
        self.create_user_and_login(email='usera@example.com', full_name='User A')
        with app.app_context():
            user_a = User.query.filter_by(email='usera@example.com').first()
            upload_a = ResumeUpload(
                user_id=user_a.id,
                filename='resume_a.pdf',
                original_filename='resume_a.pdf',
                file_path='resume_a.pdf',
                file_size=2048,
                is_active=True
            )
            db.session.add(upload_a)
            db.session.commit()
            resume_a_id = upload_a.id

        # Register and login as User B
        self.app.get('/logout')
        self.create_user_and_login(email='userb@example.com', full_name='User B')

        # User B attempts to access User A's resume
        res = self.app.post('/api/set-active-resume', json={'resume_id': resume_a_id})
        self.assertEqual(res.status_code, 404, "User B must not be able to set User A's resume active")

        # User B queries their resumes list
        list_res = self.app.get('/api/resumes')
        self.assertEqual(list_res.status_code, 200)
        list_data = json.loads(list_res.data)
        resumes_b = list_data.get('resumes', [])
        self.assertEqual(len(resumes_b), 0, "User B must have 0 resumes initially")


if __name__ == '__main__':
    unittest.main()
