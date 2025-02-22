from dotenv import load_dotenv
load_dotenv()  # .env dosyasını yükle

import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import db, init_db
import cv2

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Initialize database
init_db(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen önce giriş yapın.'

# Import models after db initialization to avoid circular imports
from models import User, AuthorizedPlate, PlateRecord, AuthorizationHistory, CameraSettings

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Bu sayfaya erişim yetkiniz yok.')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Add API token auth decorator after the role_required decorator
def api_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_token = request.headers.get('X-API-Token')
        if not api_token:
            return jsonify({'error': 'API token required'}), 401

        if api_token != os.environ.get("API_TOKEN", "test-token-123"):
            return jsonify({'error': 'Invalid API token'}), 401

        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
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

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password) and user.is_active:
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
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

@app.route('/users')
@login_required
@role_required(['admin'])
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/api/users', methods=['POST'])
@login_required
@role_required(['admin'])
def add_user():
    data = request.get_json()

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Bu kullanıcı adı zaten kullanılıyor'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Bu e-posta adresi zaten kullanılıyor'}), 400

    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        role=data['role']
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify(new_user.to_dict()), 201

@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    if user.username == current_user.username:
        return jsonify({'error': 'Kendi hesabınızı devre dışı bırakamazsınız'}), 400

    user.is_active = not user.is_active
    db.session.commit()

    return jsonify({'status': 'success'})

@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if user.username == current_user.username:
        return jsonify({'error': 'Kendi hesabınızı bu şekilde düzenleyemezsiniz'}), 400

    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
        user.username = data['username']

    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Bu e-posta adresi zaten kullanılıyor'}), 400
        user.email = data['email']

    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])

    if 'role' in data:
        user.role = data['role']

    db.session.commit()
    return jsonify(user.to_dict())

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.username == current_user.username:
        return jsonify({'error': 'Kendi hesabınızı silemezsiniz'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/authorized-plates')
@login_required
def authorized_plates():
    plates = AuthorizedPlate.query.all()
    return render_template('authorized_plates.html', plates=plates)

@app.route('/api/authorized-plates', methods=['GET'])
@login_required
def get_authorized_plates():
    plates = AuthorizedPlate.query.all()
    return jsonify([plate.to_dict() for plate in plates])

@app.route('/api/authorized-plates', methods=['POST'])
@login_required
def add_authorized_plate():
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

    if 'plate_number' in data:
        # Plaka numarası benzersiz olmalı
        existing_plate = AuthorizedPlate.query.filter_by(plate_number=data['plate_number']).first()
        if existing_plate and existing_plate.id != plate_id:
            return jsonify({'error': 'Bu plaka numarası zaten kullanılıyor'}), 400

        old_number = plate.plate_number
        plate.plate_number = data['plate_number']

        history = AuthorizationHistory(
            plate_number=data['plate_number'],
            action='update',
            description=f"Plaka numarası değiştirildi: {old_number} -> {data['plate_number']}",
            changed_by=current_user.username
        )
        db.session.add(history)

    if 'description' in data:
        plate.description = data['description']

    if 'sensitivity' in data:
        if current_user.role != 'admin':
            return jsonify({'error': 'Hassasiyet ayarını sadece yöneticiler değiştirebilir'}), 403

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

@app.route('/api/authorized-plates/<int:plate_id>', methods=['GET'])
@login_required
def get_plate(plate_id):
    plate = AuthorizedPlate.query.get_or_404(plate_id)
    return jsonify(plate.to_dict())

@app.route('/api/authorized-plates/<int:plate_id>', methods=['DELETE'])
@login_required
def delete_plate(plate_id):
    plate = AuthorizedPlate.query.get_or_404(plate_id)

    # Yetkilendirme geçmişi kaydı
    history = AuthorizationHistory(
        plate_number=plate.plate_number,
        action='delete',
        description=f"Plaka silindi",
        changed_by=current_user.username
    )
    db.session.add(history)

    db.session.delete(plate)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/plates', methods=['GET'])
@login_required
def get_plates():
    plates = PlateRecord.query.all()
    return jsonify([plate.to_dict() for plate in plates])

# Update /api/plates endpoint to use token auth instead of session auth
@app.route('/api/plates', methods=['POST'])
@api_token_required
def add_plate():
    plate_number = request.json.get('plate_number')
    confidence = request.json.get('confidence', 100)
    processed_by = request.json.get('processed_by', 'system')

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
        processed_by=processed_by,
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
    plate_records = PlateRecord.query.order_by(PlateRecord.timestamp.desc()).all()
    auth_history = AuthorizationHistory.query.order_by(AuthorizationHistory.timestamp.desc()).all()
    return render_template('plate_history.html', plate_records=plate_records, auth_history=auth_history)

@app.route('/camera-settings')
@login_required
@role_required(['admin'])
def camera_settings():
    cameras = CameraSettings.query.all()
    return render_template('camera_settings.html', cameras=cameras)

@app.route('/api/cameras', methods=['GET'])
@login_required
@role_required(['admin'])
def get_cameras():
    cameras = CameraSettings.query.all()
    return jsonify([camera.to_dict() for camera in cameras])

@app.route('/api/cameras', methods=['POST'])
@login_required
@role_required(['admin'])
def add_camera():
    data = request.get_json()

    if not all(k in data for k in ['name', 'ip_address']):
        return jsonify({'error': 'Kamera adı ve IP adresi gerekli'}), 400

    new_camera = CameraSettings(
        name=data['name'],
        ip_address=data['ip_address'],
        port=data.get('port', 80),
        username=data.get('username'),
        password=data.get('password'),
        settings=data.get('settings', {}),
        stream_type=data.get('stream_type', 'http'), # Added stream_type
        rtsp_path=data.get('rtsp_path', '/'), # Added rtsp_path
    )
    db.session.add(new_camera)
    db.session.commit()

    return jsonify(new_camera.to_dict()), 201

@app.route('/api/cameras/<int:camera_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_camera(camera_id):
    camera = CameraSettings.query.get_or_404(camera_id)
    return jsonify(camera.to_dict())

@app.route('/api/cameras/<int:camera_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_camera(camera_id):
    camera = CameraSettings.query.get_or_404(camera_id)
    data = request.get_json()

    if 'name' in data:
        camera.name = data['name']
    if 'ip_address' in data:
        camera.ip_address = data['ip_address']
    if 'port' in data:
        camera.port = data['port']
    if 'username' in data:
        camera.username = data['username']
    if 'password' in data:
        camera.password = data['password']
    if 'settings' in data:
        camera.settings = data['settings']
    if 'stream_type' in data:
        camera.stream_type = data['stream_type']
    if 'rtsp_path' in data:
        camera.rtsp_path = data['rtsp_path']

    db.session.commit()
    return jsonify(camera.to_dict())

@app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_camera(camera_id):
    camera = CameraSettings.query.get_or_404(camera_id)
    db.session.delete(camera)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/cameras/<int:camera_id>/toggle-status', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_camera_status(camera_id):
    camera = CameraSettings.query.get_or_404(camera_id)
    camera.is_active = not camera.is_active
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/cameras/<int:camera_id>/test-connection', methods=['POST'])
@login_required
@role_required(['admin'])
def test_camera_connection(camera_id):
    camera = CameraSettings.query.get_or_404(camera_id)

    try:
        if camera.stream_type == 'rtsp':
            # RTSP bağlantı URL'ini oluştur
            auth = f"{camera.username}:{camera.password}@" if camera.username and camera.password else ""
            rtsp_url = f"rtsp://{auth}{camera.ip_address}:{camera.port}{camera.rtsp_path}"

            # OpenCV ile RTSP stream'ine bağlanmayı dene
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                return jsonify({
                    'status': 'error',
                    'message': 'RTSP bağlantısı başarısız: Stream açılamadı'
                }), 400

            # İlk frame'i al
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return jsonify({
                    'status': 'error',
                    'message': 'RTSP bağlantısı başarısız: Frame okunamadı'
                }), 400

            camera.last_connected = datetime.utcnow()
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'RTSP bağlantısı başarılı'
            })

        else:  # HTTP bağlantısı için
            import requests
            from requests.exceptions import RequestException
            protocols = ['http', 'https']
            for protocol in protocols:
                try:
                    url = f"{protocol}://{camera.ip_address}:{camera.port}"
                    auth = None
                    if camera.username and camera.password:
                        auth = (camera.username, camera.password)

                    response = requests.get(url, auth=auth, timeout=5)
                    if response.status_code == 200:
                        camera.last_connected = datetime.utcnow()
                        db.session.commit()
                        return jsonify({
                            'status': 'success',
                            'message': f'HTTP bağlantısı başarılı (Protocol: {protocol})'
                        })
                except RequestException:
                    continue

            return jsonify({
                'status': 'error',
                'message': 'HTTP bağlantısı başarısız: Sunucuya erişilemiyor'
            }), 400

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Bağlantı testi başarısız: {str(e)}'
        }), 400

@app.route('/video_feed/<int:camera_id>')
@login_required
def video_feed(camera_id):
    def generate_frames():
        try:
            # Use application context
            with app.app_context():
                camera = CameraSettings.query.get_or_404(camera_id)
                if not camera.is_active:
                    logger.warning(f"Camera {camera_id} is not active")
                    return

                # Build RTSP URL
                auth = f"{camera.username}:{camera.password}@" if camera.username and camera.password else ""
                if camera.stream_type == 'rtsp':
                    stream_url = f"rtsp://{auth}{camera.ip_address}:{camera.port}{camera.rtsp_path}"
                else:
                    stream_url = f"http://{camera.ip_address}:{camera.port}/video_feed"

                logger.info(f"Attempting to connect to camera stream: {stream_url.replace(auth, '***@')}")

                cap = cv2.VideoCapture(stream_url)
                if not cap.isOpened():
                    logger.error(f"Failed to open camera stream: {stream_url.replace(auth, '***@')}")
                    return

                logger.info(f"Successfully connected to camera {camera_id}")

                while True:
                    success, frame = cap.read()
                    if not success:
                        logger.error(f"Failed to read frame from camera {camera_id}")
                        break
                    else:
                        ret, buffer = cv2.imencode('.jpg', frame)
                        if not ret:
                            logger.error(f"Failed to encode frame from camera {camera_id}")
                            break
                        frame = buffer.tobytes()
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                cap.release()
                logger.info(f"Camera {camera_id} stream ended")

        except Exception as e:
            logger.error(f"Error in video feed for camera {camera_id}: {str(e)}")
            return

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/active_cameras')
@login_required
def get_active_cameras():
    cameras = CameraSettings.query.filter_by(is_active=True).all()
    return jsonify([camera.to_dict() for camera in cameras])

with app.app_context():
    db.create_all()

    # Admin kullanıcısı yoksa oluştur
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)