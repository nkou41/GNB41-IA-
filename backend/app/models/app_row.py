from app import db
from datetime import datetime
import uuid


class AppRow(db.Model):
    __tablename__ = 'app_row'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_id = db.Column(db.String(36), db.ForeignKey('app_table.id'), nullable=False)
    data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'table_id': self.table_id,
            'data': json.loads(self.data),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
