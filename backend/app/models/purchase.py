from app import db
from datetime import datetime
import uuid


class Purchase(db.Model):
    __tablename__ = 'purchase'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = db.Column(db.String(36), db.ForeignKey('listing.id'), nullable=False)
    acheteur_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)

    prix_paye_centimes = db.Column(db.Integer, nullable=False)
    commission_centimes = db.Column(db.Integer, nullable=False)
    montant_vendeur_centimes = db.Column(db.Integer, nullable=False)

    stripe_session_id = db.Column(db.String(255), nullable=True)
    stripe_payment_intent = db.Column(db.String(255), nullable=True)

    statut = db.Column(db.String(20), default='en_attente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'acheteur_id': self.acheteur_id,
            'prix_paye_centimes': self.prix_paye_centimes,
            'commission_centimes': self.commission_centimes,
            'montant_vendeur_centimes': self.montant_vendeur_centimes,
            'statut': self.statut,
            'created_at': self.created_at.isoformat()
        }
