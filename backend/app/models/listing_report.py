from app import db
from datetime import datetime
import uuid


class ListingReport(db.Model):
    """Signalement d'une annonce. Pas de clé étrangère, pour conserver la trace."""
    __tablename__ = 'listing_report'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = db.Column(db.String(36), nullable=False, index=True)
    listing_titre = db.Column(db.String(120), nullable=True)
    reporter_id = db.Column(db.String(36), nullable=True, index=True)
    contact_email = db.Column(db.String(255), nullable=True)
    motif = db.Column(db.String(30), nullable=False)  # contrefacon | contenu_illegal | autre
    details = db.Column(db.Text, nullable=True)
    statut = db.Column(db.String(20), nullable=False, default='nouveau', index=True)  # nouveau | traite
    traite_par = db.Column(db.String(36), nullable=True)
    traite_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'listing_titre': self.listing_titre,
            'motif': self.motif,
            'details': self.details,
            'statut': self.statut,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
