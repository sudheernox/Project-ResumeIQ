"""
Database models for ResumeIQ
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resumes = db.relationship('ResumeUpload', backref='user', lazy=True, cascade='all, delete-orphan')
    analyses = db.relationship('ResumeAnalysis', backref='user', lazy=True, cascade='all, delete-orphan')
    job_matches = db.relationship('JobMatch', backref='user', lazy=True, cascade='all, delete-orphan')
    skill_gaps = db.relationship('SkillGap', backref='user', lazy=True, cascade='all, delete-orphan')
    roadmaps = db.relationship('LearningRoadmap', backref='user', lazy=True, cascade='all, delete-orphan')
    comparisons = db.relationship('JobComparison', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, secret_key, expires_sec=3600):
        from itsdangerous import URLSafeTimedSerializer
        s = URLSafeTimedSerializer(secret_key)
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, secret_key, max_age=3600):
        from itsdangerous import URLSafeTimedSerializer
        s = URLSafeTimedSerializer(secret_key)
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=max_age)
        except Exception:
            return None
        return User.query.get(data.get('user_id'))

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ResumeUpload(db.Model):
    __tablename__ = 'resume_uploads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    text_content = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)

    # Relationships
    analyses = db.relationship('ResumeAnalysis', backref='resume', lazy=True, cascade='all, delete-orphan')
    job_matches = db.relationship('JobMatch', backref='resume', lazy=True, cascade='all, delete-orphan')
    skill_gaps = db.relationship('SkillGap', backref='resume', lazy=True, cascade='all, delete-orphan')
    roadmaps = db.relationship('LearningRoadmap', backref='resume', lazy=True, cascade='all, delete-orphan')
    comparisons = db.relationship('JobComparison', backref='resume', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        latest_analysis = self.analyses[-1] if self.analyses else None
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'upload_time': self.upload_time.isoformat(),
            'is_active': bool(self.is_active),
            'has_analysis': latest_analysis is not None,
            'overall_score': round(latest_analysis.overall_score, 1) if latest_analysis else None
        }


class ResumeAnalysis(db.Model):
    __tablename__ = 'resume_analyses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume_uploads.id'), nullable=False)
    analysis_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Scores
    overall_score = db.Column(db.Float, default=0)
    skills_score = db.Column(db.Float, default=0)
    experience_score = db.Column(db.Float, default=0)
    education_score = db.Column(db.Float, default=0)
    keywords_score = db.Column(db.Float, default=0)
    ats_score = db.Column(db.Float, default=0)
    formatting_score = db.Column(db.Float, default=0)

    # Extracted data (stored as JSON strings)
    technical_skills = db.Column(db.Text, default='[]')
    soft_skills = db.Column(db.Text, default='[]')
    education_data = db.Column(db.Text, default='[]')
    experience_data = db.Column(db.Text, default='[]')
    projects_data = db.Column(db.Text, default='[]')
    certifications_data = db.Column(db.Text, default='[]')
    keywords_found = db.Column(db.Text, default='[]')

    # Analysis results
    strengths = db.Column(db.Text, default='[]')
    weaknesses = db.Column(db.Text, default='[]')
    recommendations = db.Column(db.Text, default='[]')
    ats_issues = db.Column(db.Text, default='[]')
    ai_insights = db.Column(db.Text, default='{}')

    def get_technical_skills(self):
        return json.loads(self.technical_skills or '[]')

    def get_soft_skills(self):
        return json.loads(self.soft_skills or '[]')

    def get_strengths(self):
        return json.loads(self.strengths or '[]')

    def get_weaknesses(self):
        return json.loads(self.weaknesses or '[]')

    def get_recommendations(self):
        return json.loads(self.recommendations or '[]')

    def get_education_data(self):
        return json.loads(self.education_data or '[]')

    def get_experience_data(self):
        return json.loads(self.experience_data or '[]')

    def get_projects_data(self):
        return json.loads(self.projects_data or '[]')

    def get_ats_issues(self):
        return json.loads(self.ats_issues or '[]')

    def get_ai_insights(self):
        return json.loads(self.ai_insights or '{}')

    def get_keywords_found(self):
        return json.loads(self.keywords_found or '[]')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'resume_id': self.resume_id,
            'analysis_time': self.analysis_time.isoformat(),
            'scores': {
                'overall': round(self.overall_score, 1),
                'skills': round(self.skills_score, 1),
                'experience': round(self.experience_score, 1),
                'education': round(self.education_score, 1),
                'keywords': round(self.keywords_score, 1),
                'ats': round(self.ats_score, 1),
                'formatting': round(self.formatting_score, 1),
            },
            'technical_skills': self.get_technical_skills(),
            'soft_skills': self.get_soft_skills(),
            'education': self.get_education_data(),
            'experience': self.get_experience_data(),
            'projects': self.get_projects_data(),
            'strengths': self.get_strengths(),
            'weaknesses': self.get_weaknesses(),
            'recommendations': self.get_recommendations(),
            'ats_issues': self.get_ats_issues(),
            'keywords_found': self.get_keywords_found(),
            'ai_insights': self.get_ai_insights(),
            'total_skills': len(self.get_technical_skills()) + len(self.get_soft_skills())
        }


class JobMatch(db.Model):
    __tablename__ = 'job_matches'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume_uploads.id'), nullable=False)
    job_role = db.Column(db.String(200))
    job_description = db.Column(db.Text)
    match_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Scores
    overall_match = db.Column(db.Float, default=0)
    skills_match = db.Column(db.Float, default=0)
    keywords_match = db.Column(db.Float, default=0)
    experience_match = db.Column(db.Float, default=0)

    # Match data
    matched_skills = db.Column(db.Text, default='[]')
    missing_skills = db.Column(db.Text, default='[]')
    partial_skills = db.Column(db.Text, default='[]')
    recommendations = db.Column(db.Text, default='[]')
    match_breakdown = db.Column(db.Text, default='{}')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'resume_id': self.resume_id,
            'job_role': self.job_role,
            'job_description': self.job_description,
            'match_time': self.match_time.isoformat(),
            'overall_match': round(self.overall_match, 1),
            'skills_match': round(self.skills_match, 1),
            'keywords_match': round(self.keywords_match, 1),
            'experience_match': round(self.experience_match, 1),
            'scores': {
                'overall': round(self.overall_match, 1),
                'skills': round(self.skills_match, 1),
                'keywords': round(self.keywords_match, 1),
                'experience': round(self.experience_match, 1),
            },
            'matched_skills': json.loads(self.matched_skills or '[]'),
            'missing_skills': json.loads(self.missing_skills or '[]'),
            'partial_skills': json.loads(self.partial_skills or '[]'),
            'recommendations': json.loads(self.recommendations or '[]'),
            'match_breakdown': json.loads(self.match_breakdown or '{}')
        }


class SkillGap(db.Model):
    __tablename__ = 'skill_gaps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume_uploads.id'), nullable=False)
    career_role = db.Column(db.String(200))
    custom_jd = db.Column(db.Text)
    analysis_time = db.Column(db.DateTime, default=datetime.utcnow)

    overall_coverage = db.Column(db.Float, default=0)
    existing_skills = db.Column(db.Text, default='[]')
    missing_technical = db.Column(db.Text, default='[]')
    missing_soft = db.Column(db.Text, default='[]')
    skills_to_improve = db.Column(db.Text, default='[]')
    priority_skills = db.Column(db.Text, default='[]')
    category_analysis = db.Column(db.Text, default='[]')
    radar_data = db.Column(db.Text, default='{}')

    def to_dict(self):
        missing_tech = json.loads(self.missing_technical or '[]')
        missing_sft = json.loads(self.missing_soft or '[]')
        return {
            'id': self.id,
            'user_id': self.user_id,
            'resume_id': self.resume_id,
            'career_role': self.career_role,
            'custom_jd': self.custom_jd,
            'analysis_time': self.analysis_time.isoformat(),
            'overall_coverage': round(self.overall_coverage, 1),
            'existing_skills': json.loads(self.existing_skills or '[]'),
            'missing_technical': missing_tech,
            'missing_soft': missing_sft,
            'skills_to_improve': json.loads(self.skills_to_improve or '[]'),
            'priority_skills': json.loads(self.priority_skills or '[]'),
            'category_analysis': json.loads(self.category_analysis or '[]'),
            'radar_data': json.loads(self.radar_data or '{}'),
            'total_missing': len(missing_tech) + len(missing_sft)
        }


class LearningRoadmap(db.Model):
    __tablename__ = 'learning_roadmaps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume_uploads.id'), nullable=False)
    career_role = db.Column(db.String(200))
    created_time = db.Column(db.DateTime, default=datetime.utcnow)
    updated_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roadmap_data = db.Column(db.Text, default='[]')
    stage_summary = db.Column(db.Text, default='{}')
    total_items = db.Column(db.Integer, default=0)
    completed_items = db.Column(db.Integer, default=0)
    progress_percentage = db.Column(db.Float, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'roadmap_id': self.id,
            'resume_id': self.resume_id,
            'career_role': self.career_role,
            'created_time': self.created_time.isoformat(),
            'updated_time': self.updated_time.isoformat() if self.updated_time else None,
            'roadmap_items': json.loads(self.roadmap_data or '[]'),
            'stage_summary': json.loads(self.stage_summary or '{}'),
            'total_items': self.total_items,
            'total_skills': self.total_items,
            'completed_items': self.completed_items,
            'progress_percentage': round(self.progress_percentage, 1),
        }


class RoadmapProgress(db.Model):
    __tablename__ = 'roadmap_progress'

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey('learning_roadmaps.id'), nullable=False)
    skill_name = db.Column(db.String(200))
    stage = db.Column(db.String(50))  # learn, practice, build, apply
    completed = db.Column(db.Boolean, default=False)
    completed_time = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'roadmap_id': self.roadmap_id,
            'skill_name': self.skill_name,
            'stage': self.stage,
            'completed': self.completed,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
        }


class JobComparison(db.Model):
    __tablename__ = 'job_comparisons'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume_uploads.id'), nullable=False)
    comparison_time = db.Column(db.DateTime, default=datetime.utcnow)
    comparisons_data = db.Column(db.Text, default='[]')
    best_match_role = db.Column(db.String(200))
    best_match_score = db.Column(db.Float, default=0)
    best_match_recommendation = db.Column(db.Text)

    def to_dict(self):
        comps = json.loads(self.comparisons_data or '[]')
        best = None
        if self.best_match_role:
            best = {
                'role': self.best_match_role,
                'match_percentage': self.best_match_score,
                'top_recommendation': self.best_match_recommendation
            }
        elif comps:
            best = comps[0]

        return {
            'id': self.id,
            'user_id': self.user_id,
            'resume_id': self.resume_id,
            'comparison_time': self.comparison_time.isoformat(),
            'comparisons': comps,
            'best_match': best,
            'total_roles': len(comps)
        }
