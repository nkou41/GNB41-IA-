from app import db
from datetime import datetime
import uuid


class Workspace(db.Model):
    __tablename__ = 'workspace'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom = db.Column(db.String(120), nullable=False)
    owner_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='workspace', cascade='all, delete-orphan')
    members = db.relationship('WorkspaceMember', backref='workspace', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat(),
            'project_count': len(self.projects)
        }


class WorkspaceMember(db.Model):
    __tablename__ = 'workspace_member'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    workspace_id = db.Column(db.String(36), db.ForeignKey('workspace.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
