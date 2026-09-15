from app import db
import uuid
import json


class Plan(db.Model):
    __tablename__ = 'plan'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = db.Column(db.String(30), unique=True, nullable=False)
    nom = db.Column(db.String(50), nullable=False)
    prix_usd = db.Column(db.Float, default=0)
    prix_xof = db.Column(db.Integer, default=0)
    credits = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    features = db.Column(db.Text, nullable=True)
    ordre = db.Column(db.Integer, default=0)
    populaire = db.Column(db.Boolean, default=False)
    actif = db.Column(db.Boolean, default=True)
    sur_devis = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'nom': self.nom,
            'prix_usd': self.prix_usd,
            'prix_xof': self.prix_xof,
            'credits': self.credits,
            'description': self.description,
            'features': json.loads(self.features) if self.features else [],
            'ordre': self.ordre,
            'populaire': bool(self.populaire),
            'actif': bool(self.actif),
            'sur_devis': bool(self.sur_devis),
        }
