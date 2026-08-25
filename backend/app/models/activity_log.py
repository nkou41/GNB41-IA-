from datetime import datetime
from app import db

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.String(36), db.ForeignKey('workspace.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # ex: 'project_created', 'member_added', 'project_deleted'
    details = db.Column(db.String(300), nullable=True)  # ex: nom du projet, email du membre
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from app.models.user import User
        user = User.query.get(self.user_id)
        return {
            'id': self.id,
            'action': self.action,
            'details': self.details,
            'username': user.username if user else '?',
            'created_at': self.created_at.isoformat()
        }
