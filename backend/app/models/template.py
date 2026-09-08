from app import db
from datetime import datetime
import uuid


class Template(db.Model):
    __tablename__ = 'template'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    auteur_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)
    nom = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    categorie = db.Column(db.String(40), default='autre')
    code_genere = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'auteur_id': self.auteur_id,
            'nom': self.nom,
            'description': self.description,
            'categorie': self.categorie,
            'created_at': self.created_at.isoformat()
        }
