from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # ex: 'vente', 'message', 'statut'
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    lien = db.Column(db.String(500), nullable=True)  # url ou route frontend a ouvrir au clic
    lu = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'titre': self.titre,
            'message': self.message,
            'lien': self.lien,
            'lu': self.lu,
            'created_at': self.created_at.isoformat()
        }
