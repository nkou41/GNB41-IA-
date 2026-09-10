from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(100), unique=True, nullable=True)
    plan = db.Column(db.String(20), default='gratuit')
    plan_expiry = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), default='user')
    google_play_connecte = db.Column(db.Boolean, default=False)
    google_play_connecte_le = db.Column(db.DateTime, nullable=True)
    google_play_package_name = db.Column(db.String(150), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'plan': self.plan or 'gratuit',
            'plan_expiry': self.plan_expiry.isoformat() if self.plan_expiry else None,
            'role': self.role or 'user',
            'google_play_connecte': bool(self.google_play_connecte),
            'google_play_connecte_le': self.google_play_connecte_le.isoformat() if self.google_play_connecte_le else None,
            'google_play_package_name': self.google_play_package_name
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
