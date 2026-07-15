import os
import re
import secrets
import smtplib
import sys
from email.message import EmailMessage

from flask import Blueprint, current_app, render_template, redirect, request, session, url_for, flash
from werkzeug.security import check_password_hash
from models import User
from extensions import db

bp = Blueprint('auth', __name__, template_folder='../templates')

VALID_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

OTP_LENGTH = 6


def generate_otp_code():
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def is_strong_password(password):
    return (
        len(password) >= 8
        and re.search(r'[A-Z]', password)
        and re.search(r'[a-z]', password)
        and re.search(r'\d', password)
        and re.search(r'[^A-Za-z0-9]', password)
    )


def is_valid_email(email):
    return bool(VALID_EMAIL_PATTERN.match(email))


def send_otp_email(recipient, otp_code):
    smtp_server = current_app.config.get('MAIL_SERVER') or os.environ.get('SMTP_SERVER')
    smtp_port = current_app.config.get('MAIL_PORT') or os.environ.get('SMTP_PORT', '587')
    smtp_username = current_app.config.get('MAIL_USERNAME') or os.environ.get('SMTP_USERNAME')
    smtp_password = current_app.config.get('MAIL_PASSWORD') or os.environ.get('SMTP_PASSWORD')
    from_email = current_app.config.get('MAIL_DEFAULT_SENDER') or os.environ.get('EMAIL_FROM', 'no-reply@school.local')
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    use_ssl = current_app.config.get('MAIL_USE_SSL', False)
    mail_suppress = current_app.config.get('MAIL_SUPPRESS_SEND', False)
    allow_fallback = current_app.config.get('ALLOW_OTP_FALLBACK', True)

    subject = 'Your Integrated School Portal Verification Code'
    body = (
        f'Your verification code is {otp_code}.\n\n'
        'Enter this code on the portal to complete your registration.'
    )

    if mail_suppress:
        print(f'[OTP SUPPRESSED] Email sending suppressed by configuration. OTP for {recipient}: {otp_code}', file=sys.stderr)
        return False

    if not (smtp_server and smtp_username and smtp_password):
        msg = f'SMTP not configured (server/user/pass missing).'
        if allow_fallback:
            print(f'[OTP FALLBACK] {msg} OTP code for {recipient}: {otp_code}', file=sys.stderr)
            return False
        raise RuntimeError(msg)

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = from_email
    message['To'] = recipient
    message.set_content(body)

    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=10)
        else:
            smtp = smtplib.SMTP(smtp_server, int(smtp_port), timeout=10)

        with smtp:
            smtp.ehlo()
            if use_tls and not use_ssl:
                smtp.starttls()
                smtp.ehlo()
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
        return True
    except Exception as exc:
        if allow_fallback:
            print(f'[OTP FALLBACK] Failed to send email ({exc}). OTP for {recipient}: {otp_code}', file=sys.stderr)
            return False
        raise


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(role=None):
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user or not user.is_active:
                return redirect(url_for('auth.login'))
            if role and user.role != role:
                flash('You are not authorized to access that page.', 'danger')
                return redirect(url_for('auth.dashboard'))
            return func(*args, **kwargs)

        return wrapper

    return decorator


@bp.route('/login', methods=['GET', 'POST'])
def login():
    user = current_user()
    if user:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '')
        user = None

        if student_id:
            user = User.query.filter_by(student_id=student_id).first()
            if not user:
                user = User.query.filter_by(email=student_id).first()

        if user and check_password_hash(user.password_hash, password):
            if not getattr(user, 'is_verified', True):
                session.clear()
                session['pending_user_id'] = user.id
                flash('Please verify your email before signing in.', 'warning')
                return redirect(url_for('auth.otp_page'))

            session.clear()
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            flash('You have been signed in successfully.', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            if user.role == 'organizer':
                return redirect(url_for('organizer.dashboard'))
            return redirect(url_for('auth.dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form_data = {
        'student_id': '',
        'full_name': '',
        'email': '',
        'course_year': '',
    }

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        course_year = request.form.get('course_year', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        terms = request.form.get('terms')

        form_data.update({
            'student_id': student_id,
            'full_name': full_name,
            'email': email,
            'course_year': course_year,
        })

        if not student_id:
            flash('Student ID is required.', 'danger')
        elif not full_name:
            flash('Full name is required.', 'danger')
        elif not email or not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
        elif User.query.filter_by(student_id=student_id).first():
            flash('Existing Student ID. Please use a different ID.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Existing email. Please use a different school email.', 'danger')
        elif not course_year:
            flash('Course/Year is required.', 'danger')
        elif password != confirm_password:
            flash('Password mismatch. Please confirm your password correctly.', 'danger')
        elif not is_strong_password(password):
            flash(
                'Weak password. Use at least 8 characters, including uppercase, lowercase, number, and special character.',
                'danger',
            )
        elif not terms:
            flash('You must agree to the school terms and policies.', 'danger')
        else:
            otp_code = generate_otp_code()
            user = User(
                student_id=student_id,
                name=full_name,
                email=email,
                course_year=course_year,
                otp_code=otp_code,
                is_verified=False,
                role='student',
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            email_sent = send_otp_email(email, otp_code)

            session.clear()
            session['pending_user_id'] = user.id
            if email_sent:
                flash(f'Registration successful. A verification code was sent to {email}.', 'success')
            else:
                flash(
                    'Registration successful, but we could not send the email notification. '
                    'Please check the code on the server console and continue below.',
                    'warning',
                )
            return redirect(url_for('auth.otp_page'))

    return render_template('register.html', form_data=form_data)


@bp.route('/otp', methods=['GET', 'POST'])
def otp_page():
    pending_user_id = session.get('pending_user_id')
    user = None
    form_email = ''

    if pending_user_id:
        user = db.session.get(User, pending_user_id)

    if request.method == 'POST':
        form_email = request.form.get('email', '').strip().lower()
        if not user and form_email:
            user = User.query.filter_by(email=form_email).first()

        if not user:
            flash('No pending verification found. Please register or sign in first.', 'danger')
            return redirect(url_for('auth.register'))

        otp = request.form.get('otp', '').strip()
        if otp == user.otp_code:
            user.otp_code = None
            db.session.commit()

            if not user.is_verified:
                user.is_verified = True
                db.session.commit()
                session.pop('pending_user_id', None)
                flash('Email verified successfully. You may now sign in.', 'success')
                return redirect(url_for('auth.login'))

            session.clear()
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            session.pop('pending_user_id', None)
            session.pop('pending_login', None)
            flash('Two-factor authentication successful. You are signed in.', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            if user.role == 'organizer':
                return redirect(url_for('organizer.dashboard'))
            return redirect(url_for('auth.dashboard'))

        flash('Invalid verification code. Please check the code and try again.', 'danger')
        form_email = user.email

    if user:
        form_email = user.email

    is_2fa = bool(user and user.is_verified)
    otp_title = 'Two-Factor Authentication' if is_2fa else 'Verify your email'
    otp_subtitle = (
        'Enter the verification code sent to your email to complete sign in.'
        if is_2fa
        else 'Enter the verification code sent to your school email to complete registration.'
    )

    return render_template(
        'verify_otp.html',
        email=form_email,
        show_email_input=not bool(user),
        otp_title=otp_title,
        otp_subtitle=otp_subtitle,
    )


@bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    return otp_page()


@bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or user.is_verified:
        flash('No pending verification for this email address.', 'danger')
        return redirect(url_for('auth.otp_page'))

    user.otp_code = generate_otp_code()
    db.session.commit()

    sent = send_otp_email(user.email, user.otp_code)
    if sent:
        flash('A new verification code has been sent to your email.', 'success')
    else:
        flash('Unable to send verification code by email. Check server logs for OTP.', 'warning')

    session['pending_user_id'] = user.id
    return redirect(url_for('auth.otp_page'))


@bp.route('/profile')
@login_required()
def profile():
    user = current_user()
    return render_template('profile.html', user=user)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required()
def edit_profile():
    user = current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not name or not email:
            flash('Name and email are required.', 'warning')
            return redirect(url_for('auth.edit_profile'))
        
        if email != user.email:
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Email already registered to another account.', 'warning')
                return redirect(url_for('auth.edit_profile'))
        
        user.name = name
        user.email = email
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('edit_profile.html', user=user)


@bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required()
def change_password():
    user = current_user()
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not current_password or not new_password or not confirm_password:
            flash('All password fields are required.', 'warning')
            return redirect(url_for('auth.change_password'))
        
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'warning')
            return redirect(url_for('auth.change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'warning')
            return redirect(url_for('auth.change_password'))
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'warning')
            return redirect(url_for('auth.change_password'))
        
        user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('change_password.html', user=user)


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/dashboard')
@login_required()
def dashboard():
    user = current_user()
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    if user.role == 'organizer':
        return redirect(url_for('organizer.dashboard'))
    # send students to voter dashboard
    return redirect(url_for('voting.voter_dashboard'))


@bp.route('/')
def index():
    return redirect(url_for('auth.login'))
