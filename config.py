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

    # Update configuration options
    # For Debian: dpkg configuration file behavior
    # 'keep' = keep current config, 'new' = install new config, 'old' = keep old without prompting
    DPKG_CONFOLD = True  # Keep existing config files by default
    DPKG_CONFNEW = False  # Don't automatically install new config files
