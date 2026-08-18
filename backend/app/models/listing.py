from app import db
from datetime import datetime
import uuid


class Listing(db.Model):
    __tablename__ = 'listing'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendeur_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=True)

    titre = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    prix_centimes = db.Column(db.Integer, nullable=False)
    devise = db.Column(db.String(3), default='EUR')

    source_type = db.Column(db.String(20), nullable=False, default='gnb41')
    fichier_zip_path = db.Column(db.String(255), nullable=True)
    lien_externe = db.Column(db.String(500), nullable=True)
    favicon_url = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    categorie = db.Column(db.String(30), default='autre')
    tags = db.Column(db.String(300), nullable=True)

    statut = db.Column(db.String(20), default='publie')
    commission_pourcentage = db.Column(db.Integer, default=20)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'vendeur_id': self.vendeur_id,
            'project_id': self.project_id,
            'titre': self.titre,
            'description': self.description,
            'prix_centimes': self.prix_centimes,
            'devise': self.devise,
            'source_type': self.source_type,
            'fichier_zip_path': self.fichier_zip_path,
            'lien_externe': self.lien_externe,
            'favicon_url': self.favicon_url,
            'image_url': self.image_url,
            'categorie': self.categorie,
            'tags': self.tags,
            'statut': self.statut,
            'commission_pourcentage': self.commission_pourcentage,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
