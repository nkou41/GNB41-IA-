from app import db
from datetime import datetime
import uuid


class StudioUsageLog(db.Model):
    __tablename__ = 'studio_usage_log'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = db.Column(db.String(36), db.ForeignKey('studio_api_key.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(120), nullable=False)
    statut_http = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'statut_http': self.statut_http,
            'created_at': self.created_at.isoformat(),
        }
