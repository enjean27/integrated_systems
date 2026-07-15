from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Event, Registration, Attendance, Election, Vote, Candidate, User
from extensions import db
from routes.auth_routes import login_required, current_user

bp = Blueprint('organizer', __name__, template_folder='../templates')


@bp.route('/organizer/dashboard')
@login_required(role='organizer')
def dashboard():
    user = current_user()
    events = user.events if user else []
    event_count = len(events)
    registration_count = 0
    attendance_count = 0
    election_count = 0
    if user:
        registration_count = Registration.query.join(Event, Registration.event_id == Event.id).filter(Event.organizer_id == user.id).count()
        attendance_count = Attendance.query.join(Event, Attendance.event_id == Event.id).filter(Event.organizer_id == user.id).count()
        election_count = Election.query.join(Event, Election.event_id == Event.id).filter(Event.organizer_id == user.id).count()
    stats = {
        'events': event_count,
        'registrations': registration_count,
        'attendance': attendance_count,
        'elections': election_count,
    }
    return render_template('organizer_dashboard.html', user=user, events=events, stats=stats)


@bp.route('/organizer/election_monitoring')
@login_required(role='organizer')
def election_monitoring():
    user = current_user()
    elections = Election.query.join(Event, Election.event_id == Event.id).filter(Event.organizer_id == user.id).order_by(Election.created_at.desc()).all()
    monitored = []
    for election in elections:
        event = Event.query.get(election.event_id) if election.event_id else None
        voted_count = Vote.query.filter_by(election_id=election.id).count()
        if election.event_id and event:
            total_voters = Registration.query.filter_by(event_id=event.id, status='confirmed').count()
        else:
            total_voters = User.query.filter_by(role='student', active=True).count()
        remaining_voters = max(0, total_voters - voted_count)
        candidates = Candidate.query.filter_by(election_id=election.id).order_by(Candidate.created_at.asc()).all()
        progress = int((voted_count / total_voters * 100) if total_voters else 0)
        monitored.append({
            'election': election,
            'event': event,
            'status': election.status.capitalize(),
            'voted_count': voted_count,
            'remaining_voters': remaining_voters,
            'total_voters': total_voters,
            'candidates': candidates,
            'progress': progress,
        })
    return render_template('organizer_election_monitoring.html', user=user, monitored=monitored)


@bp.route('/organizer/elections/<int:election_id>/open')
@login_required(role='organizer')
def open_election(election_id):
    user = current_user()
    election = Election.query.get_or_404(election_id)
    if not election.event_id or Event.query.get(election.event_id).organizer_id != user.id:
        flash('You are not authorized to manage this election.', 'warning')
        return redirect(url_for('organizer.election_monitoring'))
    election.status = 'open'
    db.session.commit()
    flash('Election opened successfully.', 'success')
    return redirect(url_for('organizer.election_monitoring'))


@bp.route('/organizer/elections/<int:election_id>/close')
@login_required(role='organizer')
def close_election(election_id):
    user = current_user()
    election = Election.query.get_or_404(election_id)
    if not election.event_id or Event.query.get(election.event_id).organizer_id != user.id:
        flash('You are not authorized to manage this election.', 'warning')
        return redirect(url_for('organizer.election_monitoring'))
    election.status = 'closed'
    db.session.commit()
    flash('Election closed successfully.', 'success')
    return redirect(url_for('organizer.election_monitoring'))


@bp.route('/organizer/events/create', methods=['GET', 'POST'])
@login_required(role='organizer')
def create_event():
    user = current_user()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        has_voting = bool(request.form.get('has_voting'))

        if not title:
            flash('Please enter a title for the event.', 'warning')
            return redirect(url_for('organizer.create_event'))

        date_value = None
        time_value = None
        try:
            if event_date:
                date_value = datetime.strptime(event_date, '%Y-%m-%d').date()
            if event_time:
                time_value = datetime.strptime(event_time, '%H:%M').time()
        except ValueError:
            flash('Please use a valid date and time format.', 'warning')
            return redirect(url_for('organizer.create_event'))

        event = Event(
            title=title,
            description=description,
            location=location,
            event_date=date_value,
            event_time=time_value,
            organizer_id=user.id,
            status='published',
            has_voting=has_voting,
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully.', 'success')
        return redirect(url_for('organizer.dashboard'))

    return render_template(
        'create_event.html',
        user=user,
        event=None,
        page_title='Create New Event',
        submit_label='Publish Event',
        form_action=url_for('organizer.create_event'),
    )


@bp.route('/organizer/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required(role='organizer')
def edit_event(event_id):
    user = current_user()
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != user.id:
        flash('You are not authorized to edit this event.', 'warning')
        return redirect(url_for('events.my_events'))

    if request.method == 'POST':
        event.title = request.form.get('title', '').strip() or event.title
        event.description = request.form.get('description', '').strip()
        event.location = request.form.get('location', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        event.status = request.form.get('status', event.status) or event.status
        event.has_voting = bool(request.form.get('has_voting'))

        try:
            event.event_date = datetime.strptime(event_date, '%Y-%m-%d').date() if event_date else None
            event.event_time = datetime.strptime(event_time, '%H:%M').time() if event_time else None
        except ValueError:
            flash('Please use a valid date and time format.', 'warning')
            return redirect(url_for('organizer.edit_event', event_id=event.id))

        db.session.commit()
        flash('Event updated successfully.', 'success')
        return redirect(url_for('organizer.my_events'))

    return render_template(
        'create_event.html',
        user=user,
        event=event,
        page_title='Update Event Information',
        submit_label='Save Changes',
        form_action=url_for('organizer.edit_event', event_id=event.id),
    )
