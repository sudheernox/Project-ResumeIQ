"""
ResumeIQ Configuration
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'resumeiq-hackfest-2024-secret-key-super-secure')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'resumeiq.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File Upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # AI API
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    # NLP settings
    USE_AI_API = os.getenv('USE_AI_API', 'false').lower() == 'true'

    # Email / SMTP Configuration (for secure password reset)
    MAIL_SERVER = os.getenv('MAIL_SERVER') or os.getenv('SMTP_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT') or os.getenv('SMTP_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') or os.getenv('SMTP_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD') or os.getenv('SMTP_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('SMTP_FROM', 'noreply@resumeiq.ai')
