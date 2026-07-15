from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date
from models import Event, Registration, Attendance, Certificate, User, Election
from extensions import db
from routes.auth_routes import login_required, current_user
from sqlalchemy import or_

bp = Blueprint('events', __name__, template_folder='../templates')


@bp.route('/events')
@login_required()
def index():
    user = current_user()
    # search support
    q = request.args.get('q', '').strip()
    base_q = Event.query

    # Show organizer's own events to organizers; admins see all events.
    if user.role == 'organizer':
        base_q = base_q.filter_by(organizer_id=user.id)
    elif user.role != 'admin':
        # regular users see published events by organizers/admins only
        base_q = base_q.filter_by(status='published')

    if q:
        like = f"%{q}%"
        base_q = base_q.filter(or_(Event.title.ilike(like), Event.description.ilike(like)))

    # ensure events are created by organizers/admins (for public listing)
    if user.role != 'admin' and user.role != 'organizer':
        base_q = base_q.join(User, Event.organizer_id == User.id).filter(User.role.in_(['organizer', 'admin']))

    events = base_q.order_by(Event.created_at.desc()).all()

    # categorize events by date
    upcoming = []
    ongoing = []
    finished = []
    for event in events:
        if event.event_date:
            if event.event_date > date.today():
                upcoming.append(event)
            elif event.event_date == date.today():
                ongoing.append(event)
            else:
                finished.append(event)
        else:
            upcoming.append(event)

    # preload elections for events with voting enabled
    event_ids = [e.id for e in events if e.has_voting]
    elections = {}
    if event_ids:
        rows = Election.query.filter(Election.event_id.in_(event_ids)).all()
        for r in rows:
            elections[r.event_id] = r

    return render_template(
        'events.html',
        upcoming_events=upcoming,
        ongoing_events=ongoing,
        finished_events=finished,
        elections=elections,
        user=user,
        q=q,
    )


@bp.route('/events/register/<int:event_id>', methods=['POST'])
@login_required(role='student')
def register_event(event_id):
    user = current_user()
    event = Event.query.get_or_404(event_id)
    existing = Registration.query.filter_by(event_id=event.id, user_id=user.id).first()
    if existing:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.event_detail', event_id=event.id))
    db.session.add(Registration(event_id=event.id, user_id=user.id, status='confirmed'))
    db.session.commit()
    flash('Registration successful.', 'success')
    return redirect(url_for('events.event_detail', event_id=event.id))


def ensure_event_election(event: Event):
    """If event.has_voting and there's no election yet, create a default Election linked to the event."""
    if not event.has_voting:
        return None
    existing = Election.query.filter_by(event_id=event.id).first()
    if existing:
        return existing
    # create a minimal election entry
    e = Election(title=f"Election for {event.title}", description=f"Auto-generated election for event {event.title}", event_id=event.id, status='open')
    db.session.add(e)
    db.session.commit()
    return e


@bp.route('/events/<int:event_id>', methods=['GET', 'POST'])
@login_required()
def event_detail(event_id):
    user = current_user()
    event = Event.query.get_or_404(event_id)
    registration = Registration.query.filter_by(event_id=event.id, user_id=user.id).first()
    if request.method == 'POST':
        if user.role != 'student':
            flash('Only students may register for events.', 'warning')
            return redirect(url_for('events.event_detail', event_id=event.id))
        if registration:
            flash('You are already registered for this event.', 'info')
        else:
            db.session.add(Registration(event_id=event.id, user_id=user.id, status='confirmed'))
            db.session.commit()
            flash('Registration submitted successfully.', 'success')
        return redirect(url_for('events.event_detail', event_id=event.id))

    attendance = Attendance.query.filter_by(event_id=event.id, user_id=user.id).first()
    certificate = Certificate.query.filter_by(event_id=event.id, user_id=user.id).first()
    return render_template('event_detail.html', event=event, registration=registration, attendance=attendance, certificate=certificate, user=user)


@bp.route('/events/attendance')
@login_required()
def attendance():
    user = current_user()
    records = Attendance.query.filter_by(user_id=user.id).order_by(Attendance.time_in.desc()).all()
    return render_template('attendance.html', records=records, user=user)


@bp.route('/events/certificates')
@login_required()
def certificates():
    user = current_user()
    records = Certificate.query.filter_by(user_id=user.id).order_by(Certificate.issued_at.desc()).all()
    return render_template('certificates.html', records=records, user=user)


@bp.route('/events/my')
@login_required()
def my_events():
    user = current_user()
    if user.role == 'organizer':
        events = Event.query.filter_by(organizer_id=user.id).order_by(Event.created_at.desc()).all()
    else:
        # fetch events user registered to
        events = Event.query.join(Registration, Registration.event_id == Event.id).filter(Registration.user_id == user.id).order_by(Event.created_at.desc()).all()

    for event in events:
        event.registration_count = Registration.query.filter_by(event_id=event.id).count()
        event.attendance_count = Attendance.query.filter_by(event_id=event.id).count()
    return render_template('my_events.html', events=events, user=user)


@bp.route('/events/notifications')
@login_required()
def notifications():
    user = current_user()
    # placeholder notifications - integrate with real notifications later
    notifications = []
    return render_template('notifications.html', notifications=notifications, user=user)
