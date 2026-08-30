from app import db
from datetime import datetime
import uuid


class ProjectVersion(db.Model):
    __tablename__ = 'project_version'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(20), default='claude')
    code_genere = db.Column(db.Text)
    statut = db.Column(db.String(20), default='en_generation')
    erreur_message = db.Column(db.Text)
    comprehension = db.Column(db.Text)
    plan = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'prompt': self.prompt,
            'provider': self.provider,
            'code_genere': self.code_genere,
            'statut': self.statut,
            'erreur_message': self.erreur_message,
            'comprehension': self.comprehension,
            'plan': self.plan,
            'created_at': self.created_at.isoformat()
        }
