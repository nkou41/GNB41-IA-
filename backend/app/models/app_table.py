from app import db
from datetime import datetime
import uuid


class AppTable(db.Model):
    __tablename__ = 'app_table'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=False)
    nom = db.Column(db.String(60), nullable=False)
    colonnes = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'project_id': self.project_id,
            'nom': self.nom,
            'colonnes': json.loads(self.colonnes),
            'created_at': self.created_at.isoformat()
        }
