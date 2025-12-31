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

    # Authentication settings
    AUTH_TYPE = os.environ.get('AUTH_TYPE') or 'local'  # 'local' or 'ldap'

    # LDAP settings (for future integration)
    LDAP_HOST = os.environ.get('LDAP_HOST') or 'ldap://localhost'
    LDAP_PORT = int(os.environ.get('LDAP_PORT') or 389)
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN') or 'dc=example,dc=com'
    LDAP_USER_DN = os.environ.get('LDAP_USER_DN') or 'ou=users,dc=example,dc=com'
    LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN') or ''
    LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD') or ''
    LDAP_USERNAME_ATTRIBUTE = os.environ.get('LDAP_USERNAME_ATTRIBUTE') or 'uid'
    LDAP_USE_TLS = os.environ.get('LDAP_USE_TLS', 'False').lower() == 'true'
