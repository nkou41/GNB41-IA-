from app import db
from datetime import datetime
import uuid
import secrets
import hashlib


class ApiKey(db.Model):
    __tablename__ = 'api_key'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=False)
    key_prefix = db.Column(db.String(14), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False, unique=True)
    revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_key():
        raw = 'gnb41_' + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        prefix = raw[:14]
        return raw, prefix, key_hash

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'key_prefix': self.key_prefix,
            'revoked': self.revoked,
            'created_at': self.created_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }
