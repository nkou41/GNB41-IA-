from app import db
from datetime import datetime
import uuid


class Payment(db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    transaction_id = db.Column(db.String(64), unique=True, nullable=False)
    plan_slug = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
