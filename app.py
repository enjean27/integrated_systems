import os
import sys
from pathlib import Path
from flask import Flask, redirect, session, url_for
from flask_mail import Mail

try:
    from .extensions import db
    from .models import User, Event, Registration, Attendance, Certificate, Election, Vote
    from .routes.auth_routes import bp as auth_bp
    from .routes.admin_routes import bp as admin_bp
    from .routes.organizer_routes import bp as organizer_bp
    from .routes.results_routes import bp as results_bp
    from .routes.event_routes import bp as events_bp
    from .routes.voting_routes import bp as voting_bp
except ImportError:
    from extensions import db
    from models import User, Event, Registration, Attendance, Certificate, Election, Vote
    from routes.auth_routes import bp as auth_bp
    from routes.admin_routes import bp as admin_bp
    from routes.organizer_routes import bp as organizer_bp
    from routes.results_routes import bp as results_bp
    from routes.event_routes import bp as events_bp
    from routes.voting_routes import bp as voting_bp

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'integrated-portal-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(INSTANCE_DIR / 'integrated_portal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD

db.init_app(app)
mail = Mail(app)

with app.app_context():
    db.create_all()
    # Ensure new columns exist for lightweight schema updates (SQLite)
    try:
        cols = [r[1] for r in db.engine.execute("PRAGMA table_info('events')").fetchall()]
        if 'image_url' not in cols:
            db.engine.execute("ALTER TABLE events ADD COLUMN image_url VARCHAR(255)")
        if 'event_time' not in cols:
            db.engine.execute("ALTER TABLE events ADD COLUMN event_time TIME")
    except Exception:
        # ignore if DB doesn't support pragma or already updated
        pass
    try:
        user_cols = [r[1] for r in db.engine.execute("PRAGMA table_info('users')").fetchall()]
        if 'otp_code' not in user_cols:
            db.engine.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6)")
        if 'otp_expires_at' not in user_cols:
            db.engine.execute("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME")
    except Exception:
        # ignore if DB doesn't support pragma or already updated
        pass
    if not User.query.filter_by(email='admin@school.local').first():
        admin = User(name='Admin User', email='admin@school.local', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

    if not User.query.filter_by(student_id='241-1681').first():
        admin_event = User(
            student_id='241-1681',
            name='Event Admin',
            email='eventadmin@school.local',
            course_year='BSIT 4th Year',
            role='admin',
            is_verified=True,
        )
        admin_event.set_password('admin123')
        db.session.add(admin_event)
    if not User.query.filter_by(email='organizer@school.local').first():
        organizer = User(name='Organizer User', email='organizer@school.local', role='organizer')
        organizer.set_password('organizer123')
        db.session.add(organizer)
    if not User.query.filter_by(email='student@school.local').first():
        student = User(name='Student User', email='student@school.local', role='student')
        student.set_password('student123')
        db.session.add(student)

    if not User.query.filter_by(student_id='241-1655').first():
        voter = User(
            student_id='241-1655',
            name='Voter User',
            email='voter@school.local',
            course_year='BSIT 3rd Year',
            role='student',
            is_verified=True,
        )
        voter.set_password('voter123')
        db.session.add(voter)
    db.session.commit()

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(organizer_bp)
app.register_blueprint(results_bp)
app.register_blueprint(events_bp)
app.register_blueprint(voting_bp)


@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))


@app.route('/voting/login')
def voting_login_redirect():
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
