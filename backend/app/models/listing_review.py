from app import db
from datetime import datetime
import uuid


class ListingReview(db.Model):
    """Dossier de modération d'une annonce.
    Pas de clé étrangère : le journal doit survivre à la suppression de l'annonce ou du compte."""
    __tablename__ = 'listing_review'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = db.Column(db.String(36), nullable=False, index=True)
    listing_titre = db.Column(db.String(120), nullable=True)
    vendeur_id = db.Column(db.String(36), nullable=True, index=True)
    motif = db.Column(db.String(30), nullable=False)  # marque_detectee | signalement | modification
    terme = db.Column(db.String(120), nullable=True)
    justification = db.Column(db.Text, nullable=True)
    statut = db.Column(db.String(20), nullable=False, default='en_attente', index=True)  # en_attente | approuve | refuse | retire
    decide_par = db.Column(db.String(36), nullable=True)
    decision_motif = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'listing_titre': self.listing_titre,
            'vendeur_id': self.vendeur_id,
            'motif': self.motif,
            'terme': self.terme,
            'justification': self.justification,
            'statut': self.statut,
            'decision_motif': self.decision_motif,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
        }
