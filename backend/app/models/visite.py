from app import db
from datetime import date


class Visite(db.Model):
    __tablename__ = 'visite'
    __table_args__ = (db.UniqueConstraint('project_id', 'jour', name='uq_visite_projet_jour'),)

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), nullable=False, index=True)
    jour = db.Column(db.Date, nullable=False, default=date.today)
    nombre = db.Column(db.Integer, nullable=False, default=0)
