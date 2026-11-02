"""
ResumeIQ — Main Flask Application
Hackfest 3.0 Project
"""
import os
import uuid
import json
import re
import time
import traceback
from collections import defaultdict
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from flask_cors import CORS

from config import Config
from backend.database import (
    db, User, ResumeUpload, ResumeAnalysis, JobMatch, SkillGap,
    LearningRoadmap, RoadmapProgress, JobComparison, PasswordResetToken
)
from backend.email_service import send_password_reset_email, is_smtp_configured
from backend.resume_parser import parse_resume
from backend.resume_analyzer import analyze_resume
from backend.job_matcher import match_resume_to_job, compare_multiple_jobs, ROLE_PROFILES
from backend.skill_gap import compute_skill_gap
from backend.ats_optimizer import analyze_ats
from backend.roadmap_generator import generate_roadmap
from backend.ai_service import get_ai_insights, generate_nlp_insights


def init_db_schema(app):
    """Safely initialize and migrate SQLite schema if columns were added."""
    with app.app_context():
        db.create_all()
        try:
            with db.engine.connect() as conn:
                # Add user_id column to tables if not present
                tables_with_user = [
                    'resume_uploads', 'resume_analyses', 'job_matches',
                    'skill_gaps', 'learning_roadmaps', 'job_comparisons'
                ]
                for tbl in tables_with_user:
                    res = conn.execute(db.text(f"PRAGMA table_info({tbl})")).fetchall()
                    cols = [r[1] for r in res]
                    if 'user_id' not in cols:
                        conn.execute(db.text(f"ALTER TABLE {tbl} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                        conn.commit()

                # resume_uploads
                res_u = conn.execute(db.text("PRAGMA table_info(resume_uploads)")).fetchall()
                cols_u = [r[1] for r in res_u]
                if 'is_active' not in cols_u:
                    conn.execute(db.text("ALTER TABLE resume_uploads ADD COLUMN is_active BOOLEAN DEFAULT 0"))
                    conn.commit()

                # resume_analyses
                res_a = conn.execute(db.text("PRAGMA table_info(resume_analyses)")).fetchall()
                cols_a = [r[1] for r in res_a]
                if 'ai_insights' not in cols_a:
                    conn.execute(db.text("ALTER TABLE resume_analyses ADD COLUMN ai_insights TEXT DEFAULT '{}'"))
                    conn.commit()

                # job_matches
                res_m = conn.execute(db.text("PRAGMA table_info(job_matches)")).fetchall()
                cols_m = [r[1] for r in res_m]
                if 'match_breakdown' not in cols_m:
                    conn.execute(db.text("ALTER TABLE job_matches ADD COLUMN match_breakdown TEXT DEFAULT '{}'"))
                    conn.commit()

                # skill_gaps
                res_g = conn.execute(db.text("PRAGMA table_info(skill_gaps)")).fetchall()
                cols_g = [r[1] for r in res_g]
                if 'custom_jd' not in cols_g:
                    conn.execute(db.text("ALTER TABLE skill_gaps ADD COLUMN custom_jd TEXT"))
                    conn.commit()
                if 'priority_skills' not in cols_g:
                    conn.execute(db.text("ALTER TABLE skill_gaps ADD COLUMN priority_skills TEXT DEFAULT '[]'"))
                    conn.commit()
                if 'category_analysis' not in cols_g:
                    conn.execute(db.text("ALTER TABLE skill_gaps ADD COLUMN category_analysis TEXT DEFAULT '[]'"))
                    conn.commit()
                if 'overall_coverage' not in cols_g:
                    conn.execute(db.text("ALTER TABLE skill_gaps ADD COLUMN overall_coverage FLOAT DEFAULT 0"))
                    conn.commit()

                # learning_roadmaps
                res_r = conn.execute(db.text("PRAGMA table_info(learning_roadmaps)")).fetchall()
                cols_r = [r[1] for r in res_r]
                if 'stage_summary' not in cols_r:
                    conn.execute(db.text("ALTER TABLE learning_roadmaps ADD COLUMN stage_summary TEXT DEFAULT '{}'"))
                    conn.commit()

        except Exception as e:
            print("SQLite schema check note:", e)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    init_db_schema(app)

    return app


app = create_app()


@app.after_request
def add_header(response):
    """Prevent browser from caching sensitive user pages after logout."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.context_processor
def inject_user():
    """Inject authenticated user into templates."""
    user = None
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
    return {'current_user': user}


def login_required(f):
    """Decorator to protect web views and APIs from unauthenticated access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.', 'authenticated': False}), 401
            return redirect(url_for('login_page', next=request.path))

        # Ensure user exists in database
        user = User.query.get(user_id)
        if not user:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'error': 'User not found. Please log in again.', 'authenticated': False}), 401
            return redirect(url_for('login_page', next=request.path))

        return f(*args, **kwargs)
    return decorated_function


# Rate limiting state for sensitive auth endpoints (sliding window)
_reset_rate_limits = defaultdict(list)


def is_rate_limited(key, limit=5, window_seconds=900):
    """Sliding-window rate limiter: allows up to `limit` requests per `window_seconds`."""
    now = time.time()
    valid_window = [t for t in _reset_rate_limits[key] if now - t < window_seconds]
    if len(valid_window) >= limit:
        return True
    valid_window.append(now)
    _reset_rate_limits[key] = valid_window
    return False


def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


def get_current_user_id():
    """Return user_id from session or None."""
    return session.get('user_id')


def get_active_resume(requested_id=None, user_id=None):
    """
    Retrieve and maintain the persistent active resume strictly isolated per user.
    Priority:
    1. requested_id if provided and belongs to user
    2. session['active_resume_id'] if belongs to user
    3. Resume marked is_active=True for this user
    4. Most recently uploaded resume by this user
    """
    if user_id is None:
        user_id = get_current_user_id()
    if not user_id:
        return None

    # 1. Requested ID
    if requested_id:
        resume = ResumeUpload.query.filter_by(id=requested_id, user_id=user_id).first()
        if resume:
            set_active_resume_db(resume.id, user_id=user_id)
            return resume

    # 2. Session ID
    session_id = session.get('active_resume_id')
    if session_id:
        resume = ResumeUpload.query.filter_by(id=session_id, user_id=user_id).first()
        if resume:
            if not resume.is_active:
                set_active_resume_db(resume.id, user_id=user_id)
            return resume

    # 3. DB active flag for this user
    resume = ResumeUpload.query.filter_by(is_active=True, user_id=user_id).first()
    if resume:
        session['active_resume_id'] = resume.id
        return resume

    # 4. Latest uploaded by this user
    latest = ResumeUpload.query.filter_by(user_id=user_id).order_by(ResumeUpload.upload_time.desc()).first()
    if latest:
        set_active_resume_db(latest.id, user_id=user_id)
        return latest

    return None


def set_active_resume_db(resume_id, user_id=None):
    """Mark a resume as active in both session and DB for the specified user."""
    if user_id is None:
        user_id = get_current_user_id()
    if not user_id:
        return None

    try:
        # Clear active flag only on this user's resumes
        ResumeUpload.query.filter_by(user_id=user_id).update({ResumeUpload.is_active: False})
        resume = ResumeUpload.query.filter_by(id=resume_id, user_id=user_id).first()
        if resume:
            resume.is_active = True
            session['active_resume_id'] = resume.id
            db.session.commit()
            return resume
    except Exception as e:
        db.session.rollback()
        print("Failed to set active resume:", e)
    return None


# ─── Auth Page Routes ─────────────────────────────────────────────────────────

@app.route('/login')
def login_page():
    if session.get('user_id') and User.query.get(session['user_id']):
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/register')
def register_page():
    if session.get('user_id') and User.query.get(session['user_id']):
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>')
def reset_password_page(token):
    user, error = User.verify_reset_token(token)
    return render_template(
        'reset_password.html',
        token=token,
        is_valid=(user is not None),
        error_message=error
    )


@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


# ─── Application Feature Page Routes ──────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/analysis')
@login_required
def analysis():
    return render_template('analysis.html')


@app.route('/job-match')
@login_required
def job_match():
    return render_template('job_match.html')


@app.route('/skill-gap')
@login_required
def skill_gap():
    return render_template('skill_gap.html')


@app.route('/roadmap')
@login_required
def roadmap():
    return render_template('roadmap.html')


@app.route('/comparison')
@login_required
def comparison():
    return render_template('comparison.html')


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'message': 'ResumeIQ API is running',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
    })


# ─── Authentication API Endpoints ─────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """Register a new user account with secure password hashing."""
    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # Required fields validation
    if not full_name or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required.'}), 400

    # Email format validation
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        return jsonify({'error': 'Please enter a valid email address.'}), 400

    # Password length validation
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long.'}), 400

    # Password match validation
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    # Duplicate email check
    existing_user = User.query.filter(User.email.ilike(email)).first()
    if existing_user:
        return jsonify({'error': 'An account with this email address already exists.'}), 400

    try:
        new_user = User(full_name=full_name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Log in the user immediately
        session.clear()
        session['user_id'] = new_user.id
        session['user_name'] = new_user.full_name
        session['user_email'] = new_user.email

        return jsonify({
            'success': True,
            'message': 'Account registered successfully.',
            'user': new_user.to_dict(),
            'redirect': '/dashboard'
        }), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Authenticate an existing user and set session cookie."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember_me = bool(data.get('remember_me', False))

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter(User.email.ilike(email)).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password. Please try again.'}), 401

    try:
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.full_name
        session['user_email'] = user.email

        if remember_me:
            session.permanent = True
        else:
            session.permanent = False

        # Restore user's active resume into session
        user_active = ResumeUpload.query.filter_by(user_id=user.id, is_active=True).first()
        if not user_active:
            user_active = ResumeUpload.query.filter_by(user_id=user.id).order_by(ResumeUpload.upload_time.desc()).first()

        if user_active:
            user_active.is_active = True
            session['active_resume_id'] = user_active.id
            db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'user': user.to_dict(),
            'redirect': '/dashboard'
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500


@app.route('/api/auth/logout', methods=['POST', 'GET'])
def auth_logout():
    """Log out user and clear session."""
    session.clear()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully.',
        'redirect': '/login'
    })


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Get current authenticated user information."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'authenticated': False, 'user': None})

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'authenticated': False, 'user': None})

    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    })


@app.route('/api/auth/forgot-password', methods=['POST'])
def auth_forgot_password():
    """Generate a secure, single-use reset token and send reset link."""
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email address is required.'}), 400

    # Rate limiting per IP and email to protect against abuse
    client_ip = request.remote_addr or 'unknown'
    if is_rate_limited(f"ip:{client_ip}", limit=10, window_seconds=900) or is_rate_limited(f"email:{email}", limit=5, window_seconds=900):
        return jsonify({'error': 'Too many password reset requests. Please wait a few minutes before trying again.'}), 429

    generic_message = 'If an account is associated with this email address, a password reset link has been sent.'

    user = User.query.filter(User.email.ilike(email)).first()
    if not user:
        # Prevent email enumeration: return same generic response
        return jsonify({
            'success': True,
            'message': generic_message
        })

    try:
        # Create single-use token (stores only SHA-256 hash in DB)
        token = user.create_reset_token(expires_hours=1)
        reset_url = url_for('reset_password_page', token=token, _external=True)

        email_status = send_password_reset_email(user.email, reset_url)

        # If email was actually sent through SMTP / Gmail
        if email_status.get('sent'):
            return jsonify({
                'success': True,
                'email_sent': True,
                'message': f'A password reset link has been dispatched to {user.email}. Please check your inbox and spam folder.'
            })

        # If SMTP is not yet configured in environment variables
        if not email_status.get('configured'):
            response_payload = {
                'success': True,
                'email_sent': False,
                'message': generic_message,
                'notice': email_status.get('error', 'SMTP credentials not configured.')
            }
            if app.debug or app.config.get('TESTING') or app.config.get('ENV') == 'development':
                response_payload['dev_reset_url'] = reset_url
                response_payload['token'] = token
            return jsonify(response_payload)

        # If SMTP IS configured, but sending failed: report genuine error clearly
        return jsonify({
            'error': f"Failed to send email to {user.email}: {email_status.get('error')}",
            'email_sent': False
        }), 500
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Failed to process password reset request: {str(e)}'}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def auth_reset_password():
    """Verify single-use reset token and update user password."""
    data = request.get_json() or {}
    token = data.get('token', '')
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not token:
        return jsonify({'error': 'Reset token is missing.'}), 400

    user, error_msg = User.verify_reset_token(token)
    if not user:
        return jsonify({'error': error_msg or 'Invalid or expired password reset link. Please request a new one.'}), 400

    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match.'}), 400

    try:
        user.set_password(password)
        # Invalidate token immediately to prevent token reuse
        User.consume_reset_token(token)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password has been reset successfully. Please log in with your new password.',
            'redirect': '/login'
        })
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500


@app.route('/api/auth/profile', methods=['POST'])
@login_required
def auth_profile_update():
    """Update profile details (name) or password."""
    user = User.query.get(session['user_id'])
    data = request.get_json() or {}

    full_name = data.get('full_name', '').strip()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    try:
        # Update name if provided
        if full_name:
            user.full_name = full_name
            session['user_name'] = full_name

        # Update password if requested
        if current_password or new_password or confirm_password:
            if not current_password:
                return jsonify({'error': 'Current password is required to change password.'}), 400
            if not user.check_password(current_password):
                return jsonify({'error': 'Incorrect current password.'}), 400
            if not new_password or len(new_password) < 8:
                return jsonify({'error': 'New password must be at least 8 characters long.'}), 400
            if new_password != confirm_password:
                return jsonify({'error': 'New passwords do not match.'}), 400

            user.set_password(new_password)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully.',
            'user': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500


# ─── User-Isolated Resume & Analytics API Endpoints ───────────────────────────

@app.route('/api/active-resume', methods=['GET'])
@login_required
def get_active_resume_api():
    """Get the currently active resume and its latest analysis for the authenticated user."""
    user_id = session['user_id']
    requested_id = request.args.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)

    if not resume:
        return jsonify({
            'has_resume': False,
            'message': 'No resume uploaded yet'
        })

    latest_analysis = ResumeAnalysis.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        ResumeAnalysis.analysis_time.desc()).first()

    return jsonify({
        'has_resume': True,
        'resume': resume.to_dict(),
        'analysis': latest_analysis.to_dict() if latest_analysis else None
    })


@app.route('/api/set-active-resume', methods=['POST'])
@login_required
def set_active_resume_api():
    """Set the active resume by ID for the authenticated user."""
    user_id = session['user_id']
    data = request.get_json() or {}
    resume_id = data.get('resume_id')

    if not resume_id:
        return jsonify({'error': 'resume_id is required'}), 400

    resume = set_active_resume_db(resume_id, user_id=user_id)
    if not resume:
        return jsonify({'error': 'Resume not found or does not belong to user'}), 404

    latest_analysis = ResumeAnalysis.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        ResumeAnalysis.analysis_time.desc()).first()

    return jsonify({
        'success': True,
        'message': f'Active resume set to {resume.original_filename}',
        'resume': resume.to_dict(),
        'analysis': latest_analysis.to_dict() if latest_analysis else None
    })


@app.route('/api/resumes', methods=['GET'])
@login_required
def list_resumes_api():
    """List all uploaded resumes strictly belonging to the authenticated user."""
    user_id = session['user_id']
    resumes = ResumeUpload.query.filter_by(user_id=user_id).order_by(ResumeUpload.upload_time.desc()).all()
    active_resume = get_active_resume(user_id=user_id)
    active_id = active_resume.id if active_resume else None

    result = []
    for r in resumes:
        info = r.to_dict()
        info['is_active'] = (r.id == active_id)
        result.append(info)

    return jsonify({
        'resumes': result,
        'total': len(result),
        'active_id': active_id
    })


@app.route('/api/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    """Upload and parse a resume file under the authenticated user's workspace."""
    user_id = session['user_id']

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDF and DOCX are supported.'}), 400

    try:
        # Save file securely
        original_filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(file_path)

        file_size = os.path.getsize(file_path)

        # Parse resume text & sections
        parsed = parse_resume(file_path)

        # Unmark user's previous active resumes
        ResumeUpload.query.filter_by(user_id=user_id).update({ResumeUpload.is_active: False})

        # Store resume record bound strictly to this user
        resume_record = ResumeUpload(
            user_id=user_id,
            filename=unique_name,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            text_content=parsed['raw_text'],
            is_active=True
        )
        db.session.add(resume_record)
        db.session.commit()

        # Update Flask session
        session['active_resume_id'] = resume_record.id

        return jsonify({
            'success': True,
            'resume_id': resume_record.id,
            'filename': original_filename,
            'file_size': file_size,
            'word_count': parsed['word_count'],
            'name': parsed.get('name', 'Candidate'),
            'message': 'Resume uploaded and parsed successfully',
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 422
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Failed to process resume: {str(e)}'}), 500


@app.route('/api/analyze-resume', methods=['POST'])
@login_required
def analyze_resume_api():
    """Perform complete resume analysis for the user's active resume and persist results."""
    user_id = session['user_id']
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400

    try:
        # Parse resume from stored file
        parsed = parse_resume(resume.file_path)
        result = analyze_resume(parsed)

        # Generative AI insights or structured NLP insights
        ai_insights = get_ai_insights(parsed['raw_text'], result)
        if not ai_insights or not isinstance(ai_insights, dict):
            ai_insights = generate_nlp_insights(result) or {}

        # Embed transparent category breakdown, deductions, and ATS disclaimer
        ai_insights['category_scores'] = result.get('category_scores', {})
        ai_insights['deductions_summary'] = result.get('deductions_summary', [])
        ai_insights['ats_disclaimer'] = result.get('ats_disclaimer', '')

        # Save analysis to database bound to user
        analysis_record = ResumeAnalysis(
            user_id=user_id,
            resume_id=resume.id,
            overall_score=result['scores']['overall'],
            skills_score=result['scores']['skills'],
            experience_score=result['scores']['experience'],
            education_score=result['scores']['education'],
            keywords_score=result['scores']['keywords'],
            ats_score=result['scores']['ats'],
            formatting_score=result['scores']['formatting'],
            technical_skills=json.dumps(result['technical_skills']),
            soft_skills=json.dumps(result['soft_skills']),
            education_data=json.dumps(result['education']),
            experience_data=json.dumps(result['experience']),
            projects_data=json.dumps(result['projects']),
            strengths=json.dumps(result['strengths']),
            weaknesses=json.dumps(result['weaknesses']),
            recommendations=json.dumps(result['recommendations']),
            keywords_found=json.dumps(result['keywords_found']),
            ai_insights=json.dumps(ai_insights)
        )
        db.session.add(analysis_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'analysis_id': analysis_record.id,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            'candidate_name': parsed.get('name', 'Candidate'),
            'scores': result['scores'],
            'technical_skills': result['technical_skills'],
            'soft_skills': result['soft_skills'],
            'education': result['education'],
            'experience': result['experience'],
            'projects': result['projects'],
            'strengths': result['strengths'],
            'weaknesses': result['weaknesses'],
            'recommendations': result['recommendations'],
            'keywords_found': result['keywords_found'],
            'total_skills': result['total_skills'],
            'category_scores': result.get('category_scores', {}),
            'deductions_summary': result.get('deductions_summary', []),
            'ats_disclaimer': result.get('ats_disclaimer', ''),
            'ai_insights': ai_insights,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/api/job-match', methods=['GET', 'POST'])
@login_required
def job_match_api():
    """
    Match resume against a job description.
    GET: Retrieve latest saved job match for user's active resume.
    POST: Compute a new job match and persist it under user.
    """
    user_id = session['user_id']

    if request.method == 'GET':
        requested_id = request.args.get('resume_id')
        resume = get_active_resume(requested_id, user_id=user_id)
        if not resume:
            return jsonify({'has_match': False, 'message': 'No resume found'})

        latest_match = JobMatch.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
            JobMatch.match_time.desc()).first()
        if not latest_match:
            return jsonify({'has_match': False, 'resume_id': resume.id, 'filename': resume.original_filename})

        data = latest_match.to_dict()
        data['has_match'] = True
        data['filename'] = resume.original_filename
        return jsonify(data)

    # POST
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)

    job_title = data.get('job_title', '').strip()
    job_role = data.get('job_role', '').strip() or job_title
    job_description = data.get('job_description', '').strip()

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400
    if not job_description or len(job_description) < 15:
        return jsonify({'error': 'Please upload or paste a job description to access this feature.'}), 400

    try:
        resume_text = resume.text_content or ''
        if not resume_text and os.path.exists(resume.file_path):
            parsed = parse_resume(resume.file_path)
            resume_text = parsed['raw_text']
            resume.text_content = resume_text
            db.session.commit()

        result = match_resume_to_job(resume_text, job_description, job_role or 'Target Job')

        # Save to database bound to user
        match_record = JobMatch(
            user_id=user_id,
            resume_id=resume.id,
            job_role=job_role,
            job_description=job_description,
            overall_match=result['overall_match'],
            skills_match=result['skills_match'],
            keywords_match=result['keywords_match'],
            experience_match=result['experience_match'],
            matched_skills=json.dumps(result['matched_skills']),
            missing_skills=json.dumps(result['missing_skills']),
            partial_skills=json.dumps(result['partial_skills']),
            recommendations=json.dumps(result['recommendations']),
            match_breakdown=json.dumps(result['match_breakdown'])
        )
        db.session.add(match_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'match_id': match_record.id,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            **result,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Job matching failed: {str(e)}'}), 500


@app.route('/api/skill-gap', methods=['GET', 'POST'])
@login_required
def skill_gap_api():
    """
    Compute skill gap for a career role or custom JD.
    GET: Retrieve latest saved skill gap for user's active resume.
    POST: Compute and persist new skill gap analysis under user.
    """
    user_id = session['user_id']

    if request.method == 'GET':
        requested_id = request.args.get('resume_id')
        role = request.args.get('career_role')
        resume = get_active_resume(requested_id, user_id=user_id)
        if not resume:
            return jsonify({'has_gap': False, 'message': 'No resume found'})

        query = SkillGap.query.filter_by(resume_id=resume.id, user_id=user_id)
        if role:
            query = query.filter_by(career_role=role)
        latest_gap = query.order_by(SkillGap.analysis_time.desc()).first()

        if not latest_gap:
            return jsonify({'has_gap': False, 'resume_id': resume.id, 'filename': resume.original_filename})

        data = latest_gap.to_dict()
        data['has_gap'] = True
        data['filename'] = resume.original_filename
        return jsonify(data)

    # POST
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)
    career_role = data.get('career_role', 'Software Developer')
    custom_jd = data.get('custom_jd', '').strip()

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400

    try:
        resume_text = resume.text_content or ''
        if not resume_text and os.path.exists(resume.file_path):
            parsed = parse_resume(resume.file_path)
            resume_text = parsed['raw_text']
            resume.text_content = resume_text
            db.session.commit()

        result = compute_skill_gap(resume_text, career_role, custom_jd)

        # Save to database bound to user
        gap_record = SkillGap(
            user_id=user_id,
            resume_id=resume.id,
            career_role=career_role,
            custom_jd=custom_jd,
            overall_coverage=result['overall_coverage'],
            existing_skills=json.dumps(result['existing_skills']),
            missing_technical=json.dumps(result['missing_technical']),
            missing_soft=json.dumps(result['missing_soft']),
            skills_to_improve=json.dumps(result['skills_to_improve']),
            priority_skills=json.dumps(result['priority_skills']),
            category_analysis=json.dumps(result['category_analysis']),
            radar_data=json.dumps(result['radar_data']),
        )
        db.session.add(gap_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'gap_id': gap_record.id,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            **result,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Skill gap analysis failed: {str(e)}'}), 500


@app.route('/api/roadmap', methods=['GET'])
@login_required
def get_roadmap_api():
    """Retrieve existing saved learning roadmap for user's active resume."""
    user_id = session['user_id']
    requested_id = request.args.get('resume_id')
    role = request.args.get('career_role')
    resume = get_active_resume(requested_id, user_id=user_id)

    if not resume:
        return jsonify({'has_roadmap': False, 'message': 'No resume found'})

    query = LearningRoadmap.query.filter_by(resume_id=resume.id, user_id=user_id)
    if role:
        query = query.filter_by(career_role=role)
    latest_roadmap = query.order_by(LearningRoadmap.updated_time.desc()).first()

    if not latest_roadmap:
        return jsonify({'has_roadmap': False, 'resume_id': resume.id, 'filename': resume.original_filename})

    data = latest_roadmap.to_dict()
    data['has_roadmap'] = True
    data['filename'] = resume.original_filename
    return jsonify(data)


@app.route('/api/generate-roadmap', methods=['POST'])
@login_required
def generate_roadmap_api():
    """Generate a personalized learning roadmap using identified skill gaps under user."""
    user_id = session['user_id']
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)
    career_role = data.get('career_role', 'Software Developer')
    missing_skills = data.get('missing_skills', [])

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400

    try:
        # If no missing skills provided, derive from job description, latest skill gap, or compute
        if not missing_skills:
            job_desc = (data.get('job_description') or '').strip()
            if job_desc:
                resume_text = resume.text_content or ''
                match_res = match_resume_to_job(resume_text, job_desc, career_role)
                missing_skills = match_res.get('missing_skills', [])
            else:
                gap = SkillGap.query.filter_by(resume_id=resume.id, user_id=user_id, career_role=career_role).order_by(
                    SkillGap.analysis_time.desc()).first()
                if gap:
                    missing_skills = json.loads(gap.missing_technical or '[]') + json.loads(gap.missing_soft or '[]')
                elif career_role:
                    resume_text = resume.text_content or ''
                    gap_result = compute_skill_gap(resume_text, career_role)
                    missing_skills = gap_result.get('missing_technical', []) + gap_result.get('missing_soft', [])

        if not missing_skills:
            return jsonify({'error': 'No missing skills identified. Please upload or paste a job description to generate a learning roadmap.'}), 400

        result = generate_roadmap(missing_skills[:12], career_role)

        # Save to database bound to user
        roadmap_record = LearningRoadmap(
            user_id=user_id,
            resume_id=resume.id,
            career_role=career_role,
            roadmap_data=json.dumps(result['roadmap_items']),
            stage_summary=json.dumps(result.get('stage_summary', {})),
            total_items=result['total_skills'],
            completed_items=0,
            progress_percentage=0,
        )
        db.session.add(roadmap_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'roadmap_id': roadmap_record.id,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            **result,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Roadmap generation failed: {str(e)}'}), 500


@app.route('/api/roadmap-progress', methods=['POST'])
@login_required
def update_roadmap_progress():
    """Update roadmap item completion status and persist progress in SQLite."""
    user_id = session['user_id']
    data = request.get_json() or {}
    roadmap_id = data.get('roadmap_id')
    skill_name = data.get('skill_name')
    completed = data.get('completed', True)

    if not roadmap_id or not skill_name:
        return jsonify({'error': 'roadmap_id and skill_name are required'}), 400

    try:
        # Verify roadmap belongs to user
        roadmap = LearningRoadmap.query.filter_by(id=roadmap_id, user_id=user_id).first()
        if not roadmap:
            return jsonify({'error': 'Roadmap not found or access denied'}), 404

        items = json.loads(roadmap.roadmap_data or '[]')
        for item in items:
            if item['skill'].lower() == skill_name.lower():
                item['completed'] = completed
                break

        completed_count = sum(1 for i in items if i.get('completed'))
        total = len(items)
        progress = round((completed_count / max(total, 1)) * 100, 1)

        roadmap.roadmap_data = json.dumps(items)
        roadmap.completed_items = completed_count
        roadmap.progress_percentage = progress
        roadmap.updated_time = datetime.utcnow()

        # Update or create RoadmapProgress record
        prog_rec = RoadmapProgress.query.filter_by(roadmap_id=roadmap.id, skill_name=skill_name).first()
        if not prog_rec:
            prog_rec = RoadmapProgress(roadmap_id=roadmap.id, skill_name=skill_name)
            db.session.add(prog_rec)
        prog_rec.completed = completed
        prog_rec.completed_time = datetime.utcnow() if completed else None

        db.session.commit()

        return jsonify({
            'success': True,
            'skill_name': skill_name,
            'completed': completed,
            'completed_items': completed_count,
            'total_items': total,
            'progress_percentage': progress,
        })

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare-jobs', methods=['GET', 'POST'])
@login_required
def compare_jobs_api():
    """
    Compare resume against multiple job profiles.
    GET: Retrieve existing saved comparison for user's active resume.
    POST: Compute comparison, persist in SQLite, and return.
    """
    user_id = session['user_id']

    if request.method == 'GET':
        requested_id = request.args.get('resume_id')
        resume = get_active_resume(requested_id, user_id=user_id)
        if not resume:
            return jsonify({'has_comparison': False, 'message': 'No resume found'})

        latest_comp = JobComparison.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
            JobComparison.comparison_time.desc()).first()
        if not latest_comp:
            return jsonify({'has_comparison': False, 'resume_id': resume.id, 'filename': resume.original_filename})

        data = latest_comp.to_dict()
        data['has_comparison'] = True
        data['filename'] = resume.original_filename
        return jsonify(data)

    # POST
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)
    selected_roles = data.get('roles', [])
    custom_roles = data.get('custom_roles', [])
    jobs = data.get('jobs', [])

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400

    # Strict validation: Require at least two valid job inputs for comparison
    if jobs:
        valid_jobs = [j for j in jobs if (j.get('title') or j.get('role')) and len(j.get('description', '').strip()) >= 15]
        if len(valid_jobs) < 2:
            return jsonify({'error': 'Please provide at least two valid job descriptions for comparison.'}), 400
    elif not selected_roles and not custom_roles:
        return jsonify({'error': 'Please provide at least two valid job descriptions for comparison.'}), 400

    try:
        resume_text = resume.text_content or ''
        if not resume_text and os.path.exists(resume.file_path):
            parsed = parse_resume(resume.file_path)
            resume_text = parsed['raw_text']
            resume.text_content = resume_text
            db.session.commit()

        results = compare_multiple_jobs(
            resume_text,
            job_roles=selected_roles or None,
            custom_roles=custom_roles or None,
            jobs=jobs or None
        )
        best = results[0] if results else None

        # Save to database bound to user
        comp_record = JobComparison(
            user_id=user_id,
            resume_id=resume.id,
            comparisons_data=json.dumps(results),
            best_match_role=best['role'] if best else None,
            best_match_score=best['match_percentage'] if best else 0,
            best_match_recommendation=best.get('top_recommendation') if best else ''
        )
        db.session.add(comp_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'comparison_id': comp_record.id,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            'comparisons': results,
            'best_match': best,
            'total_roles': len(results),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Job comparison failed: {str(e)}'}), 500


@app.route('/api/ats-analysis', methods=['POST'])
@login_required
def ats_analysis_api():
    """Analyze ATS compatibility for the active resume."""
    user_id = session['user_id']
    data = request.get_json() or {}
    requested_id = data.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)
    target_role = data.get('target_role', '')

    if not resume:
        return jsonify({'error': 'No resume found. Please upload a resume first.'}), 400

    try:
        resume_text = resume.text_content or ''
        if not resume_text and os.path.exists(resume.file_path):
            parsed = parse_resume(resume.file_path)
            resume_text = parsed['raw_text']
            resume.text_content = resume_text
            db.session.commit()

        result = analyze_ats(resume_text, target_role)

        return jsonify({
            'success': True,
            'resume_id': resume.id,
            'filename': resume.original_filename,
            **result,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'ATS analysis failed: {str(e)}'}), 500


@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard_api():
    """Get dashboard summary data for the user's active resume."""
    user_id = session['user_id']
    requested_id = request.args.get('resume_id')
    resume = get_active_resume(requested_id, user_id=user_id)

    if not resume:
        return jsonify({
            'has_data': False,
            'message': 'No resume uploaded yet',
        })

    # Latest analysis for this resume & user
    analysis = ResumeAnalysis.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        ResumeAnalysis.analysis_time.desc()).first()

    # Latest job match
    job_match = JobMatch.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        JobMatch.match_time.desc()).first()

    # Latest skill gap
    skill_gap = SkillGap.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        SkillGap.analysis_time.desc()).first()

    # Latest roadmap
    roadmap = LearningRoadmap.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        LearningRoadmap.created_time.desc()).first()

    # Latest comparison
    comparison = JobComparison.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
        JobComparison.comparison_time.desc()).first()

    missing_skills_count = len(json.loads(skill_gap.missing_technical or '[]')) if skill_gap else 0

    return jsonify({
        'has_data': True,
        'resume': resume.to_dict(),
        'analysis': analysis.to_dict() if analysis else None,
        'job_match': job_match.to_dict() if job_match else None,
        'skill_gap': skill_gap.to_dict() if skill_gap else None,
        'roadmap': roadmap.to_dict() if roadmap else None,
        'comparison': comparison.to_dict() if comparison else None,
        'summary': {
            'overall_score': analysis.overall_score if analysis else 0,
            'ats_score': analysis.ats_score if analysis else 0,
            'job_match': job_match.overall_match if job_match else 0,
            'total_skills': len(analysis.get_technical_skills()) if analysis else 0,
            'missing_skills': missing_skills_count,
            'roadmap_progress': roadmap.progress_percentage if roadmap else 0,
        }
    })


@app.route('/api/analysis-history', methods=['GET'])
@login_required
def analysis_history():
    """Get resume analysis history for current user."""
    user_id = session['user_id']
    resumes = ResumeUpload.query.filter_by(user_id=user_id).order_by(ResumeUpload.upload_time.desc()).limit(15).all()
    active_resume = get_active_resume(user_id=user_id)
    active_id = active_resume.id if active_resume else None

    history = []
    for resume in resumes:
        analysis = ResumeAnalysis.query.filter_by(resume_id=resume.id, user_id=user_id).order_by(
            ResumeAnalysis.analysis_time.desc()).first()
        info = resume.to_dict()
        info['score'] = round(analysis.overall_score, 1) if analysis else None
        info['ats_score'] = round(analysis.ats_score, 1) if analysis else None
        info['analyzed'] = analysis is not None
        info['is_active'] = (resume.id == active_id)
        history.append(info)

    return jsonify({'history': history, 'total': len(history), 'active_id': active_id})


@app.route('/api/delete-resume/<int:resume_id>', methods=['DELETE'])
@login_required
def delete_resume(resume_id):
    """Delete a resume and all associated analyses, verifying user ownership."""
    user_id = session['user_id']
    resume = ResumeUpload.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return jsonify({'error': 'Resume not found or does not belong to user'}), 404

    try:
        deleted_name = resume.original_filename
        was_active = resume.is_active or (session.get('active_resume_id') == resume_id)

        # Delete file from disk if present
        if os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except Exception as e:
                print("Note on removing file:", e)

        db.session.delete(resume)
        db.session.commit()

        # If deleted resume was active, set user's next available resume active
        new_active = None
        if was_active:
            session.pop('active_resume_id', None)
            new_active = ResumeUpload.query.filter_by(user_id=user_id).order_by(ResumeUpload.upload_time.desc()).first()
            if new_active:
                set_active_resume_db(new_active.id, user_id=user_id)

        return jsonify({
            'success': True,
            'message': f'Resume "{deleted_name}" deleted successfully',
            'has_resumes': new_active is not None,
            'active_resume': new_active.to_dict() if new_active else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/roles', methods=['GET'])
def get_roles():
    """Get available job roles."""
    return jsonify({'roles': list(ROLE_PROFILES.keys())})


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
