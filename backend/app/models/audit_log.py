from app import db
from datetime import datetime
from sqlalchemy import event
import uuid


class AuditLog(db.Model):
    """Journal d'audit en ajout seul. Pas de clé étrangère : il survit à la suppression d'un compte."""
    __tablename__ = 'audit_log'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = db.Column(db.String(36), nullable=True, index=True)
    admin_email = db.Column(db.String(120), nullable=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    cible_type = db.Column(db.String(30), nullable=True)
    cible_id = db.Column(db.String(64), nullable=True)
    ancienne_valeur = db.Column(db.Text, nullable=True)
    nouvelle_valeur = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    ip_chaine = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id, 'admin_email': self.admin_email, 'action': self.action,
            'cible_type': self.cible_type, 'cible_id': self.cible_id,
            'ancienne_valeur': self.ancienne_valeur, 'nouvelle_valeur': self.nouvelle_valeur,
            'ip': self.ip, 'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@event.listens_for(AuditLog, 'before_update')
def _interdire_modification(mapper, connection, target):
    raise RuntimeError("Le journal d'audit est en ajout seul")


@event.listens_for(AuditLog, 'before_delete')
def _interdire_suppression(mapper, connection, target):
    raise RuntimeError("Le journal d'audit est en ajout seul")
