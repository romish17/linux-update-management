from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class Server(db.Model):
    __tablename__ = 'servers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(100), nullable=False)
    ssh_key_path = db.Column(db.String(500))
    os_type = db.Column(db.String(50), nullable=False)  # 'debian' or 'almalinux'
    last_check = db.Column(db.DateTime)
    updates_available = db.Column(db.Integer, default=0)
    security_updates_count = db.Column(db.Integer, default=0)  # Number of security updates
    critical_cves_count = db.Column(db.Integer, default=0)  # Number of critical CVEs
    status = db.Column(db.String(50), default='unknown')  # 'online', 'offline', 'updating', 'unknown'
    auto_check = db.Column(db.Boolean, default=True)  # Enable automatic update checking
    check_interval = db.Column(db.Integer, default=6)  # Check interval in hours
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updates = db.relationship('UpdateHistory', back_populates='server', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'os_type': self.os_type,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'updates_available': self.updates_available,
            'security_updates_count': self.security_updates_count,
            'critical_cves_count': self.critical_cves_count,
            'status': self.status,
            'auto_check': self.auto_check,
            'check_interval': self.check_interval,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UpdateHistory(db.Model):
    __tablename__ = 'update_history'

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    server_hostname = db.Column(db.String(255))  # Stored for historical tracking
    action = db.Column(db.String(50), nullable=False)  # 'check', 'update', 'security_update', 'error'
    update_type = db.Column(db.String(50), default='all')  # 'all', 'security'
    packages_count = db.Column(db.Integer, default=0)
    package_list = db.Column(db.Text)  # JSON array of package details
    security_count = db.Column(db.Integer, default=0)  # Number of security updates
    cve_list = db.Column(db.Text)  # JSON array of CVE details
    critical_cves = db.Column(db.Text)  # JSON array of critical CVE IDs
    output = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True)
    duration = db.Column(db.Float)  # Duration in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    server = db.relationship('Server', back_populates='updates')

    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server.name if self.server else None,
            'server_hostname': self.server_hostname,
            'action': self.action,
            'update_type': self.update_type,
            'packages_count': self.packages_count,
            'package_list': json.loads(self.package_list) if self.package_list else [],
            'security_count': self.security_count,
            'cve_list': json.loads(self.cve_list) if self.cve_list else [],
            'critical_cves': json.loads(self.critical_cves) if self.critical_cves else [],
            'output': self.output,
            'success': self.success,
            'duration': self.duration,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ScheduledUpdate(db.Model):
    __tablename__ = 'scheduled_updates'

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    schedule_type = db.Column(db.String(20), nullable=False)  # 'weekly', 'daily', 'monthly'
    day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday (for weekly)
    day_of_month = db.Column(db.Integer)  # 1-31 (for monthly)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    minute = db.Column(db.Integer, default=0)  # 0-59
    update_type = db.Column(db.String(20), default='all')  # 'all' or 'security'
    auto_reboot = db.Column(db.Boolean, default=False)  # Reboot if needed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    server = db.relationship('Server', backref='schedules')

    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server.name if self.server else None,
            'enabled': self.enabled,
            'schedule_type': self.schedule_type,
            'day_of_week': self.day_of_week,
            'day_of_month': self.day_of_month,
            'hour': self.hour,
            'minute': self.minute,
            'update_type': self.update_type,
            'auto_reboot': self.auto_reboot,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_cron_expression(self):
        """Generate cron expression from schedule"""
        if self.schedule_type == 'daily':
            return f"{self.minute} {self.hour} * * *"
        elif self.schedule_type == 'weekly':
            return f"{self.minute} {self.hour} * * {self.day_of_week}"
        elif self.schedule_type == 'monthly':
            return f"{self.minute} {self.hour} {self.day_of_month} * *"
        return None


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    auth_type = db.Column(db.String(20), default='local')  # 'local' or 'ldap'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'auth_type': self.auth_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
