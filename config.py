import os
import sys
from dotenv import load_dotenv

# Only load dotenv if the file exists
if os.path.exists('.env'):
    load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change'
    
    # Nile Database Configuration
    # Priority order: NILEDB_URL > POSTGRES_URL > DATABASE_URL > SQLite fallback
    database_url = (os.environ.get('NILEDB_URL') or 
                   os.environ.get('POSTGRES_URL') or 
                   os.environ.get('DATABASE_URL'))
    
    # Fix for Postgres connection strings - ensure postgresql:// protocol
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Database configuration
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"Using Nile/PostgreSQL database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    else:
        # Fallback to SQLite for local development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///brandcartel.db'
        print("Using SQLite database for local development")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Nile Database specific settings
    NILEDB_USER = os.environ.get('NILEDB_USER')
    NILEDB_PASSWORD = os.environ.get('NILEDB_PASSWORD')
    NILEDB_API_URL = os.environ.get('NILEDB_API_URL')
    NILEDB_POSTGRES_URL = os.environ.get('NILEDB_POSTGRES_URL')
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # For Vercel, use /tmp directory for file uploads
    if os.environ.get('VERCEL_ENV') == 'production':
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        UPLOAD_FOLDER = 'static/uploads'
    
    # Disable template caching for troubleshooting
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True
    
    # Maximum file upload size
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
