from app import db


class NotificationPreference(db.Model):
    __tablename__ = 'notification_preferences'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'categorie', name='uq_notif_pref_user_cat'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False, index=True)
    categorie = db.Column(db.String(30), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
