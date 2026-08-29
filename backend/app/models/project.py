from app import db
from datetime import datetime
import uuid


class Project(db.Model):
    __tablename__ = 'project'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = db.Column(db.String(36), db.ForeignKey('workspace.id'), nullable=False)
    nom = db.Column(db.String(120), nullable=False)
    prompt_initial = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(20), default='claude')
    statut = db.Column(db.String(20), default='en_attente')
    code_genere = db.Column(db.Text)
    est_deploye = db.Column(db.Boolean, default=False)
    erreur_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'nom': self.nom,
            'prompt_initial': self.prompt_initial,
            'provider': self.provider,
            'statut': self.statut,
            'code_genere': self.code_genere,
            'est_deploye': self.est_deploye,
            'erreur_message': self.erreur_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
