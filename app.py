import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen önce giriş yapın.'

# Mock user database (replace with proper database in production)
USERS = {
    "admin": generate_password_hash("admin123")
}

class User:
    def __init__(self, username):
        self.username = username
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.username

@login_manager.user_loader
def load_user(username):
    if username in USERS:
        return User(username)
    return None

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USERS and check_password_hash(USERS[username], password):
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Geçersiz kullanıcı adı veya şifre')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/authorized-plates')
@login_required
def authorized_plates():
    from models import AuthorizedPlate
    plates = AuthorizedPlate.query.all()
    return render_template('authorized_plates.html', plates=plates)

@app.route('/api/authorized-plates', methods=['GET'])
@login_required
def get_authorized_plates():
    from models import AuthorizedPlate
    plates = AuthorizedPlate.query.all()
    return jsonify([plate.to_dict() for plate in plates])

@app.route('/api/authorized-plates', methods=['POST'])
@login_required
def add_authorized_plate():
    from models import AuthorizedPlate
    data = request.get_json()
    plate_number = data.get('plate_number')
    description = data.get('description', '')

    if not plate_number:
        return jsonify({'error': 'Plaka numarası gerekli'}), 400

    existing_plate = AuthorizedPlate.query.filter_by(plate_number=plate_number).first()
    if existing_plate:
        return jsonify({'error': 'Bu plaka zaten tanımlı'}), 400

    new_plate = AuthorizedPlate(plate_number=plate_number, description=description)
    db.session.add(new_plate)
    db.session.commit()

    return jsonify(new_plate.to_dict()), 201

@app.route('/api/authorized-plates/<int:plate_id>', methods=['PUT'])
@login_required
def update_authorized_plate(plate_id):
    from models import AuthorizedPlate, AuthorizationHistory
    plate = AuthorizedPlate.query.get_or_404(plate_id)
    data = request.get_json()

    if 'is_active' in data:
        old_status = plate.is_active
        plate.is_active = data['is_active']

        # Yetkilendirme geçmişi kaydı
        action = 'activate' if data['is_active'] else 'deactivate'
        history = AuthorizationHistory(
            plate_number=plate.plate_number,
            action=action,
            description=f"Plaka durumu değiştirildi: {'aktif' if data['is_active'] else 'pasif'}",
            changed_by=current_user.username
        )
        db.session.add(history)

    if 'description' in data:
        plate.description = data['description']

    if 'sensitivity' in data:
        plate.sensitivity = data['sensitivity']
        history = AuthorizationHistory(
            plate_number=plate.plate_number,
            action='update',
            description=f"Hassasiyet ayarı güncellendi: {data['sensitivity']}",
            changed_by=current_user.username
        )
        db.session.add(history)

    db.session.commit()
    return jsonify(plate.to_dict())

@app.route('/api/plates', methods=['GET'])
@login_required
def get_plates():
    from models import PlateRecord
    plates = PlateRecord.query.all()
    return jsonify([plate.to_dict() for plate in plates])

@app.route('/api/plates', methods=['POST'])
@login_required
def add_plate():
    from models import AuthorizedPlate, PlateRecord
    plate_number = request.json.get('plate_number')
    confidence = request.json.get('confidence', 100)

    # Yetkili plaka kontrolü
    authorized_plate = AuthorizedPlate.query.filter_by(
        plate_number=plate_number, 
        is_active=True
    ).first()

    is_authorized = bool(authorized_plate)
    if authorized_plate:
        authorized_plate.last_access = datetime.utcnow()
        if confidence < authorized_plate.sensitivity:
            is_authorized = False
        db.session.commit()

    action_taken = "Kapı Açıldı" if is_authorized else "Erişim Reddedildi"
    new_plate = PlateRecord(
        plate_number=plate_number,
        confidence=confidence,
        is_authorized=is_authorized,
        processed_by=current_user.username,
        action_taken=action_taken
    )
    db.session.add(new_plate)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'is_authorized': is_authorized,
        'action_taken': action_taken
    })

@app.route('/plate-history')
@login_required
def plate_history():
    from models import PlateRecord, AuthorizationHistory
    plate_records = PlateRecord.query.order_by(PlateRecord.timestamp.desc()).all()
    auth_history = AuthorizationHistory.query.order_by(AuthorizationHistory.timestamp.desc()).all()
    return render_template('plate_history.html', plate_records=plate_records, auth_history=auth_history)

with app.app_context():
    from models import AuthorizedPlate, PlateRecord, AuthorizationHistory
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)