from app import db
from datetime import datetime
import uuid
import secrets
import hashlib


class StudioApiKey(db.Model):
    __tablename__ = 'studio_api_key'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    nom = db.Column(db.String(80), nullable=False)
    environnement = db.Column(db.String(10), default='live')  # 'test' ou 'live'
    key_prefix = db.Column(db.String(28), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False, unique=True)
    revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_key(environnement='live'):
        raw = f'gnb41_sk_{environnement}_' + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        prefix = raw[:28]
        return raw, prefix, key_hash

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'environnement': self.environnement,
            'key_prefix': self.key_prefix,
            'revoked': self.revoked,
            'created_at': self.created_at.isoformat(),
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
        }
