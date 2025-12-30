from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

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
    status = db.Column(db.String(50), default='unknown')  # 'online', 'offline', 'updating', 'unknown'
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
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UpdateHistory(db.Model):
    __tablename__ = 'update_history'

    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'check', 'update', 'error'
    packages_count = db.Column(db.Integer, default=0)
    output = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    server = db.relationship('Server', back_populates='updates')

    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server.name if self.server else None,
            'action': self.action,
            'packages_count': self.packages_count,
            'output': self.output,
            'success': self.success,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
