import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen önce giriş yapın.'

# Mock user database (replace with proper database in production)
USERS = {
    "admin": generate_password_hash("admin123")
}

# Mock plate storage
PLATES_FILE = "plates.json"

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

@app.route('/api/plates', methods=['GET'])
@login_required
def get_plates():
    try:
        with open(PLATES_FILE, 'r') as f:
            plates = json.load(f)
    except FileNotFoundError:
        plates = []
    return jsonify(plates)

@app.route('/api/plates', methods=['POST'])
@login_required
def add_plate():
    plate_number = request.json.get('plate_number')
    confidence = request.json.get('confidence', 100)

    try:
        with open(PLATES_FILE, 'r') as f:
            plates = json.load(f)
    except FileNotFoundError:
        plates = []

    plates.append({
        'plate_number': plate_number,
        'confidence': confidence,
        'timestamp': datetime.now().isoformat()
    })

    with open(PLATES_FILE, 'w') as f:
        json.dump(plates, f)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)