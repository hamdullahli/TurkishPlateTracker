from datetime import datetime
from app import db

class AuthorizedPlate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_access': self.last_access.isoformat() if self.last_access else None
        }

class PlateRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_authorized = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'plate_number': self.plate_number,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'is_authorized': self.is_authorized
        }