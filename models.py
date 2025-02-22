from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='operator')  # admin, manager, operator
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class AuthorizedPlate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime)
    sensitivity = db.Column(db.Float, default=85.0)  # Plaka tanıma hassasiyeti ayarı

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_access': self.last_access.isoformat() if self.last_access else None,
            'sensitivity': self.sensitivity
        }

class PlateRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_authorized = db.Column(db.Boolean, default=False)
    processed_by = db.Column(db.String(64))  # İşlemi yapan kullanıcı
    action_taken = db.Column(db.String(50))  # Yapılan işlem (örn: "Kapı Açıldı", "Erişim Reddedildi")

    def to_dict(self):
        return {
            'plate_number': self.plate_number,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'is_authorized': self.is_authorized,
            'processed_by': self.processed_by,
            'action_taken': self.action_taken
        }

class AuthorizationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'activate', 'deactivate', 'update'
    description = db.Column(db.String(200))
    changed_by = db.Column(db.String(64), nullable=False)  # Değişikliği yapan kullanıcı
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'action': self.action,
            'description': self.description,
            'changed_by': self.changed_by,
            'timestamp': self.timestamp.isoformat()
        }