import uuid
from datetime import datetime
from app import db


class EvaluationRun(db.Model):
    __tablename__ = 'evaluation_runs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    suite_id = db.Column(db.String(36), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(20))
    statut = db.Column(db.String(20))
    a_comprehension = db.Column(db.Boolean, default=False)
    a_plan = db.Column(db.Boolean, default=False)
    nb_fichiers = db.Column(db.Integer, default=0)
    nb_avertissements = db.Column(db.Integer, default=0)
    duree_ms = db.Column(db.Integer)
    erreur = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'suite_id': self.suite_id,
            'prompt': self.prompt,
            'provider': self.provider,
            'statut': self.statut,
            'a_comprehension': self.a_comprehension,
            'a_plan': self.a_plan,
            'nb_fichiers': self.nb_fichiers,
            'nb_avertissements': self.nb_avertissements,
            'duree_ms': self.duree_ms,
            'erreur': self.erreur,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
