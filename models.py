from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    course_year = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    otp_code = db.Column(db.String(12), nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(30), nullable=False, default='student')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login-style attributes (app uses `user.is_active` check).
    # Keep these simple since this app uses session-based auth.
    @property
    def is_active(self):
        return self.active if self.active is not None else True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    event_time = db.Column(db.Time, nullable=True)
    event_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='published')
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    organizer = db.relationship('User', backref='events')
    has_voting = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='confirmed')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    time_in = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='on_time')


class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)


class Election(db.Model):
    __tablename__ = 'elections'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    status = db.Column(db.String(20), default='draft')
    start_datetime = db.Column(db.DateTime, nullable=True)
    end_datetime = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    choice = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    position = db.Column(db.String(100), nullable=False, index=True)
    partylist = db.Column(db.String(120), nullable=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def vote_count(self):
        return Vote.query.filter_by(choice=str(self.id)).count()
