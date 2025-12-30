import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///updates.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SSH settings
    SSH_TIMEOUT = 30
    UPDATE_CHECK_INTERVAL = 3600  # 1 hour in seconds
