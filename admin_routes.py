import csv
import io
import json
import os
from datetime import datetime, date
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from models import User, Event, Election, Registration, Vote, Candidate, Certificate, Position, Attendance
from extensions import db
from routes.auth_routes import login_required, current_user
from settings_store import load_settings, save_settings, STATIC_UPLOAD_DIR
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, template_folder='../templates')

ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}


def allowed_logo_filename(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


@bp.route('/admin')
@login_required(role='admin')
def dashboard():
    user = current_user()
    counts = {
        'students': User.query.filter_by(role='student').count(),
        'events': Event.query.count(),
        'active_elections': Election.query.filter(Election.status == 'open').count(),
        'votes_cast': Vote.query.count(),
        'certificates': Certificate.query.count(),
    }
    return render_template('admin_dashboard.html', user=user, counts=counts)


# Management panels (placeholders)
@bp.route('/admin/manage_users')
@login_required(role='admin')
def manage_users():
    user = current_user()
    users = User.query.order_by(User.created_at.desc()).limit(200).all()
    return render_template('admin_manage_users.html', user=user, users=users)


@bp.route('/admin/manage_users/add', methods=['GET', 'POST'])
@login_required(role='admin')
def add_user():
    user = current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')

        if role == 'voter':
            role = 'student'
        if role not in ('student', 'organizer', 'admin'):
            role = 'student'

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'warning')
            return redirect(url_for('admin.add_user'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('admin.add_user'))

        new_user = User(name=name, email=email, role=role, active=True)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('New user added successfully.', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template(
        'admin_create_user.html',
        user=user,
        target_user=None,
        page_title='Add User',
        submit_label='Add User',
        form_action=url_for('admin.add_user'),
    )


@bp.route('/admin/manage_users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_user(user_id):
    admin = current_user()
    target = User.query.get_or_404(user_id)

    if request.method == 'POST':
        target.name = request.form.get('name', '').strip() or target.name
        email = request.form.get('email', '').strip().lower()
        if email and email != target.email:
            if User.query.filter_by(email=email).first():
                flash('Email already registered to another account.', 'warning')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            target.email = email

        role = request.form.get('role', 'student')
        if role == 'voter':
            role = 'student'
        target.role = role if role in ('student', 'organizer', 'admin') else target.role

        password = request.form.get('password', '').strip()
        if password:
            target.set_password(password)

        target.active = request.form.get('active') == 'on'
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template(
        'admin_create_user.html',
        user=admin,
        target_user=target,
        page_title='Edit User',
        submit_label='Save Changes',
        form_action=url_for('admin.edit_user', user_id=user_id),
    )


@bp.route('/admin/manage_users/<int:user_id>/delete')
@login_required(role='admin')
def delete_user(user_id):
    target = User.query.get_or_404(user_id)
    current = current_user()
    if target.id == current.id:
        flash('You cannot delete your own account while signed in.', 'warning')
        return redirect(url_for('admin.manage_users'))
    db.session.delete(target)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.manage_users'))


@bp.route('/admin/manage_users/<int:user_id>/toggle_active')
@login_required(role='admin')
def toggle_user_active(user_id):
    target = User.query.get_or_404(user_id)
    target.active = not target.active
    db.session.commit()
    flash(f"User account {'activated' if target.active else 'deactivated'} successfully.", 'success')
    return redirect(url_for('admin.manage_users'))


@bp.route('/admin/manage_users/<int:user_id>/reset_password')
@login_required(role='admin')
def reset_user_password(user_id):
    target = User.query.get_or_404(user_id)
    default_password = 'Password123!'
    target.set_password(default_password)
    db.session.commit()
    flash(f"Password reset to {default_password}. Share this with the user securely.", 'success')
    return redirect(url_for('admin.manage_users'))


@bp.route('/admin/manage_organizers')
@login_required(role='admin')
def manage_organizers():
    user = current_user()
    organizers = User.query.filter_by(role='organizer').all()
    return render_template('admin_manage_organizers.html', user=user, organizers=organizers)


@bp.route('/admin/manage_events')
@login_required(role='admin')
def manage_events():
    user = current_user()
    events = Event.query.order_by(Event.created_at.desc()).all()
    organizer_ids = [event.organizer_id for event in events if event.organizer_id]
    organizers = User.query.filter(User.id.in_(organizer_ids)).all() if organizer_ids else []
    organizer_names = {organizer.id: organizer.name for organizer in organizers}
    return render_template('admin_manage_events.html', user=user, events=events, organizer_names=organizer_names)


@bp.route('/admin/manage_events/create', methods=['GET', 'POST'])
@login_required(role='admin')
def create_event():
    user = current_user()
    organizers = User.query.filter_by(role='organizer').all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        status = request.form.get('status', 'upcoming')
        organizer_id = request.form.get('organizer_id')
        event_date = request.form.get('event_date')
        event_time = request.form.get('event_time')

        if not title:
            flash('Event title is required.', 'warning')
            return redirect(url_for('admin.create_event'))

        event = Event(
            title=title,
            description=description,
            location=location,
            status=status if status in ('upcoming', 'ongoing', 'completed', 'cancelled') else 'upcoming',
        )

        if organizer_id and organizer_id.isdigit():
            event.organizer_id = int(organizer_id)

        if event_date:
            try:
                event.event_date = date.fromisoformat(event_date)
            except ValueError:
                flash('Invalid event date.', 'warning')
                return redirect(url_for('admin.create_event'))

        if event_time:
            try:
                event.event_time = datetime.fromisoformat(f'1970-01-01T{event_time}').time()
            except ValueError:
                flash('Invalid event time.', 'warning')
                return redirect(url_for('admin.create_event'))

        db.session.add(event)
        db.session.commit()
        flash('Event created successfully.', 'success')
        return redirect(url_for('admin.manage_events'))

    return render_template(
        'admin_event_form.html',
        user=user,
        page_title='Create Event',
        submit_label='Create Event',
        event=None,
        organizers=organizers,
        statuses=['upcoming', 'ongoing', 'completed', 'cancelled'],
        form_action=url_for('admin.create_event'),
    )


@bp.route('/admin/manage_events/<int:event_id>/view')
@login_required(role='admin')
def view_event(event_id):
    user = current_user()
    event = Event.query.get_or_404(event_id)
    organizer = User.query.get(event.organizer_id) if event.organizer_id else None
    registrations = Registration.query.filter_by(event_id=event.id).count()
    attendances = Attendance.query.filter_by(event_id=event.id).count()
    certificates = Certificate.query.filter_by(event_id=event.id).count()
    election = Election.query.filter_by(event_id=event.id).first() if event.has_voting else None
    return render_template(
        'admin_event_view.html',
        user=user,
        event=event,
        organizer=organizer,
        registrations=registrations,
        attendances=attendances,
        certificates=certificates,
        election=election,
    )


@bp.route('/admin/manage_events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_event(event_id):
    user = current_user()
    event = Event.query.get_or_404(event_id)
    organizers = User.query.filter_by(role='organizer').all()
    if request.method == 'POST':
        event.title = request.form.get('title', '').strip() or event.title
        event.description = request.form.get('description', '').strip()
        event.location = request.form.get('location', '').strip()
        status = request.form.get('status', event.status)
        organizer_id = request.form.get('organizer_id')
        event_date = request.form.get('event_date')
        event_time = request.form.get('event_time')

        event.status = status if status in ('upcoming', 'ongoing', 'completed', 'cancelled') else event.status
        event.organizer_id = int(organizer_id) if organizer_id and organizer_id.isdigit() else None

        if event_date:
            try:
                event.event_date = date.fromisoformat(event_date)
            except ValueError:
                flash('Invalid event date.', 'warning')
                return redirect(url_for('admin.edit_event', event_id=event.id))
        else:
            event.event_date = None

        if event_time:
            try:
                event.event_time = datetime.fromisoformat(f'1970-01-01T{event_time}').time()
            except ValueError:
                flash('Invalid event time.', 'warning')
                return redirect(url_for('admin.edit_event', event_id=event.id))
        else:
            event.event_time = None

        db.session.commit()
        flash('Event updated successfully.', 'success')
        return redirect(url_for('admin.manage_events'))

    return render_template(
        'admin_event_form.html',
        user=user,
        page_title='Edit Event',
        submit_label='Save Changes',
        event=event,
        organizers=organizers,
        statuses=['upcoming', 'ongoing', 'completed', 'cancelled'],
        form_action=url_for('admin.edit_event', event_id=event.id),
    )


@bp.route('/admin/manage_events/<int:event_id>/delete')
@login_required(role='admin')
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    Registration.query.filter_by(event_id=event.id).delete()
    Attendance.query.filter_by(event_id=event.id).delete()
    Certificate.query.filter_by(event_id=event.id).delete()
    if event.has_voting:
        election = Election.query.filter_by(event_id=event.id).first()
        if election:
            Position.query.filter_by(election_id=election.id).delete()
            Candidate.query.filter_by(election_id=election.id).delete()
            Vote.query.filter_by(election_id=election.id).delete()
            db.session.delete(election)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('admin.manage_events'))


@bp.route('/admin/manage_events/<int:event_id>/status/<status>')
@login_required(role='admin')
def set_event_status(event_id, status):
    event = Event.query.get_or_404(event_id)
    if status in ('upcoming', 'ongoing', 'completed', 'cancelled'):
        event.status = status
        db.session.commit()
        flash(f'Event status updated to {status}.', 'success')
    else:
        flash('Invalid event status.', 'warning')
    return redirect(url_for('admin.manage_events'))


@bp.route('/admin/manage_elections')
@login_required(role='admin')
def manage_elections():
    user = current_user()
    elections = Election.query.order_by(Election.created_at.desc()).all()
    event_ids = [e.event_id for e in elections if e.event_id]
    event_titles = {}
    if event_ids:
        event_rows = Event.query.filter(Event.id.in_(event_ids)).all()
        event_titles = {event.id: event.title for event in event_rows}
    election_ids = [e.id for e in elections]
    position_rows = Position.query.filter(Position.election_id.in_(election_ids)).all() if election_ids else []
    positions_by_election = {}
    for position in position_rows:
        positions_by_election.setdefault(position.election_id, []).append(position.name)

    return render_template(
        'admin_manage_elections.html',
        user=user,
        elections=elections,
        event_titles=event_titles,
        positions_by_election=positions_by_election,
    )


@bp.route('/admin/manage_elections/create', methods=['GET', 'POST'])
@login_required(role='admin')
def create_election():
    user = current_user()
    events = Event.query.order_by(Event.created_at.desc()).all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_id = request.form.get('event_id')
        status = request.form.get('status', 'draft')
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_date = request.form.get('end_date')
        end_time = request.form.get('end_time')
        positions_raw = request.form.get('positions', '').strip()

        if not title:
            flash('Election title is required.', 'warning')
            return redirect(url_for('admin.create_election'))

        election = Election(title=title, description=description, status=status if status in ('draft', 'open', 'closed') else 'draft')
        if event_id and event_id.isdigit():
            election.event_id = int(event_id)

        if start_date and start_time:
            try:
                election.start_datetime = datetime.fromisoformat(f'{start_date}T{start_time}')
            except ValueError:
                flash('Invalid start date or time.', 'warning')
                return redirect(url_for('admin.create_election'))

        if end_date and end_time:
            try:
                election.end_datetime = datetime.fromisoformat(f'{end_date}T{end_time}')
            except ValueError:
                flash('Invalid end date or time.', 'warning')
                return redirect(url_for('admin.create_election'))

        db.session.add(election)
        db.session.commit()

        positions = [p.strip() for p in positions_raw.split(',') if p.strip()]
        for position_name in positions:
            db.session.add(Position(election_id=election.id, name=position_name))
        db.session.commit()

        flash('Election created successfully.', 'success')
        return redirect(url_for('admin.manage_elections'))

    return render_template(
        'admin_election_form.html',
        user=user,
        page_title='Create Election',
        submit_label='Create Election',
        election=None,
        events=events,
        positions='',
        statuses=['draft', 'open', 'closed'],
        form_action=url_for('admin.create_election'),
    )


@bp.route('/admin/manage_elections/<int:election_id>/view')
@login_required(role='admin')
def view_election(election_id):
    user = current_user()
    election = Election.query.get_or_404(election_id)
    event = Event.query.get(election.event_id) if election.event_id else None
    positions = Position.query.filter_by(election_id=election.id).all()
    candidates = Candidate.query.filter_by(election_id=election.id).all()
    vote_count = Vote.query.filter_by(election_id=election.id).count()
    return render_template(
        'admin_election_view.html',
        user=user,
        election=election,
        event=event,
        positions=positions,
        candidates=candidates,
        vote_count=vote_count,
    )


@bp.route('/admin/manage_elections/<int:election_id>/delete')
@login_required(role='admin')
def delete_election(election_id):
    election = Election.query.get_or_404(election_id)
    Position.query.filter_by(election_id=election.id).delete()
    Candidate.query.filter_by(election_id=election.id).delete()
    Vote.query.filter_by(election_id=election.id).delete()
    db.session.delete(election)
    db.session.commit()
    flash('Election deleted successfully.', 'success')
    return redirect(url_for('admin.manage_elections'))


@bp.route('/admin/manage_elections/<int:election_id>/open')
@login_required(role='admin')
def open_election(election_id):
    election = Election.query.get_or_404(election_id)
    election.status = 'open'
    db.session.commit()
    flash('Election opened successfully.', 'success')
    return redirect(url_for('admin.manage_elections'))


@bp.route('/admin/manage_elections/<int:election_id>/close')
@login_required(role='admin')
def close_election(election_id):
    election = Election.query.get_or_404(election_id)
    election.status = 'closed'
    db.session.commit()
    flash('Election closed successfully.', 'success')
    return redirect(url_for('admin.manage_elections'))


@bp.route('/admin/manage_elections/<int:election_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_election(election_id):
    user = current_user()
    election = Election.query.get_or_404(election_id)
    events = Event.query.order_by(Event.created_at.desc()).all()
    positions = Position.query.filter_by(election_id=election.id).all()
    positions_text = ', '.join([pos.name for pos in positions])

    if request.method == 'POST':
        election.title = request.form.get('title', '').strip() or election.title
        election.description = request.form.get('description', '').strip()
        event_id = request.form.get('event_id')
        status = request.form.get('status', election.status)
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_date = request.form.get('end_date')
        end_time = request.form.get('end_time')
        positions_raw = request.form.get('positions', '').strip()

        if event_id and event_id.isdigit():
            election.event_id = int(event_id)
        else:
            election.event_id = None

        election.status = status if status in ('draft', 'open', 'closed') else election.status

        if start_date and start_time:
            try:
                election.start_datetime = datetime.fromisoformat(f'{start_date}T{start_time}')
            except ValueError:
                flash('Invalid start date or time.', 'warning')
                return redirect(url_for('admin.edit_election', election_id=election.id))
        else:
            election.start_datetime = None

        if end_date and end_time:
            try:
                election.end_datetime = datetime.fromisoformat(f'{end_date}T{end_time}')
            except ValueError:
                flash('Invalid end date or time.', 'warning')
                return redirect(url_for('admin.edit_election', election_id=election.id))
        else:
            election.end_datetime = None

        Position.query.filter_by(election_id=election.id).delete()
        new_positions = [p.strip() for p in positions_raw.split(',') if p.strip()]
        for position_name in new_positions:
            db.session.add(Position(election_id=election.id, name=position_name))

        db.session.commit()
        flash('Election updated successfully.', 'success')
        return redirect(url_for('admin.manage_elections'))

    return render_template(
        'admin_election_form.html',
        user=user,
        page_title='Edit Election',
        submit_label='Save Changes',
        election=election,
        events=events,
        positions=positions_text,
        statuses=['draft', 'open', 'closed'],
        form_action=url_for('admin.edit_election', election_id=election.id),
    )


@bp.route('/admin/manage_candidates')
@login_required(role='admin')
def manage_candidates():
    user = current_user()
    candidates = Candidate.query.order_by(Candidate.created_at.desc()).all()
    election_ids = [c.election_id for c in candidates if c.election_id]
    elections = Election.query.filter(Election.id.in_(election_ids)).all() if election_ids else []
    election_titles = {e.id: e.title for e in elections}
    return render_template('admin_manage_candidates.html', user=user, candidates=candidates, election_titles=election_titles)


@bp.route('/admin/manage_candidates/create', methods=['GET', 'POST'])
@login_required(role='admin')
def create_candidate():
    user = current_user()
    elections = Election.query.order_by(Election.created_at.desc()).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        position = request.form.get('position', '').strip()
        partylist = request.form.get('partylist', '').strip()
        image_url = request.form.get('image_url', '').strip()
        election_id = request.form.get('election_id')

        if not name or not position or not election_id or not election_id.isdigit():
            flash('Name, position, and election are required.', 'warning')
            return redirect(url_for('admin.create_candidate'))

        candidate = Candidate(
            name=name,
            description=description,
            position=position,
            partylist=partylist,
            image_url=image_url,
            election_id=int(election_id),
        )
        db.session.add(candidate)
        db.session.commit()
        flash('Candidate added successfully.', 'success')
        return redirect(url_for('admin.manage_candidates'))

    return render_template(
        'admin_candidate_form.html',
        user=user,
        page_title='Add Candidate',
        submit_label='Add Candidate',
        candidate=None,
        elections=elections,
        form_action=url_for('admin.create_candidate'),
    )


@bp.route('/admin/manage_candidates/<int:candidate_id>/view')
@login_required(role='admin')
def view_candidate(candidate_id):
    user = current_user()
    candidate = Candidate.query.get_or_404(candidate_id)
    election = Election.query.get(candidate.election_id)
    return render_template('admin_candidate_view.html', user=user, candidate=candidate, election=election)


@bp.route('/admin/manage_candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_candidate(candidate_id):
    user = current_user()
    candidate = Candidate.query.get_or_404(candidate_id)
    elections = Election.query.order_by(Election.created_at.desc()).all()
    if request.method == 'POST':
        candidate.name = request.form.get('name', '').strip() or candidate.name
        candidate.description = request.form.get('description', '').strip()
        candidate.position = request.form.get('position', '').strip() or candidate.position
        candidate.partylist = request.form.get('partylist', '').strip()
        candidate.image_url = request.form.get('image_url', '').strip()
        election_id = request.form.get('election_id')
        candidate.election_id = int(election_id) if election_id and election_id.isdigit() else candidate.election_id

        db.session.commit()
        flash('Candidate updated successfully.', 'success')
        return redirect(url_for('admin.manage_candidates'))

    return render_template(
        'admin_candidate_form.html',
        user=user,
        page_title='Edit Candidate Information',
        submit_label='Save Candidate',
        candidate=candidate,
        elections=elections,
        form_action=url_for('admin.edit_candidate', candidate_id=candidate.id),
    )


@bp.route('/admin/manage_candidates/<int:candidate_id>/delete')
@login_required(role='admin')
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    db.session.delete(candidate)
    db.session.commit()
    flash('Candidate removed successfully.', 'success')
    return redirect(url_for('admin.manage_candidates'))


@bp.route('/admin/manage_votes')
@login_required(role='admin')
def manage_votes():
    user = current_user()
    voters = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    completed_votes = Vote.query.order_by(Vote.created_at.desc()).limit(80).all()

    recent_votes = []
    for vote in completed_votes:
        voter = User.query.get(vote.user_id)
        election = Election.query.get(vote.election_id)
        recent_votes.append(
            {
                'voter': voter.name if voter else 'Unknown Voter',
                'email': voter.email if voter else '',
                'election': election.title if election else f'Election #{vote.election_id}',
                'choice': vote.choice,
                'created_at': vote.created_at,
            }
        )

    voter_summary = []
    for voter in voters:
        votes_for_voter = Vote.query.filter_by(user_id=voter.id).order_by(Vote.created_at.desc()).all()
        voter_summary.append(
            {
                'id': voter.id,
                'name': voter.name,
                'email': voter.email,
                'active': voter.active,
                'registered_at': voter.created_at,
                'vote_count': len(votes_for_voter),
                'last_vote': votes_for_voter[0].created_at if votes_for_voter else None,
                'status_label': 'Active' if voter.active else 'Inactive',
            }
        )

    return render_template(
        'admin_manage_votes.html',
        user=user,
        voters=voter_summary,
        recent_votes=recent_votes,
    )


@bp.route('/admin/manage_votes/add', methods=['GET', 'POST'])
@login_required(role='admin')
def create_voter():
    user = current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'warning')
            return redirect(url_for('admin.create_voter'))

        if User.query.filter_by(email=email).first():
            flash('A voter with that email already exists.', 'warning')
            return redirect(url_for('admin.create_voter'))

        voter = User(name=name, email=email, role='student', active=True)
        voter.set_password(password)
        db.session.add(voter)
        db.session.commit()
        flash('Voter added successfully.', 'success')
        return redirect(url_for('admin.manage_votes'))

    return render_template('admin_voter_form.html', user=user, page_title='Add Voter', submit_label='Add Voter', voter=None, form_action=url_for('admin.create_voter'))


@bp.route('/admin/manage_votes/import', methods=['GET', 'POST'])
@login_required(role='admin')
def import_voters():
    user = current_user()
    if request.method == 'POST':
        csv_content = request.form.get('csv_content', '').strip()
        if not csv_content:
            flash('Please paste voter CSV content to import.', 'warning')
            return redirect(url_for('admin.import_voters'))

        created_count = 0
        duplicate_count = 0
        reader = csv.reader(StringIO(csv_content))
        for row in reader:
            if len(row) < 3:
                continue
            name = row[0].strip()
            email = row[1].strip().lower()
            password = row[2].strip()
            if not name or not email or not password:
                continue
            if name.lower() == 'name' and email.lower() in ('email', 'e-mail'):
                continue
            if User.query.filter_by(email=email).first():
                duplicate_count += 1
                continue
            voter = User(name=name, email=email, role='student', active=True)
            voter.set_password(password)
            db.session.add(voter)
            created_count += 1

        db.session.commit()
        flash(f'Imported {created_count} voters. Skipped {duplicate_count} duplicates.', 'success')
        return redirect(url_for('admin.manage_votes'))

    return render_template('admin_voter_import.html', user=user)


@bp.route('/admin/manage_votes/<int:voter_id>/view')
@login_required(role='admin')
def view_voter(voter_id):
    user = current_user()
    voter = User.query.get_or_404(voter_id)
    votes = Vote.query.filter_by(user_id=voter.id).order_by(Vote.created_at.desc()).all()
    vote_records = []
    for vote in votes:
        election = Election.query.get(vote.election_id)
        vote_records.append(
            {
                'election': election.title if election else f'Election #{vote.election_id}',
                'choice': vote.choice,
                'created_at': vote.created_at,
            }
        )
    return render_template('admin_voter_view.html', user=user, voter=voter, votes=vote_records)


@bp.route('/admin/manage_votes/<int:voter_id>/edit', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_voter(voter_id):
    user = current_user()
    voter = User.query.get_or_404(voter_id)
    if request.method == 'POST':
        voter.name = request.form.get('name', '').strip() or voter.name
        email = request.form.get('email', '').strip().lower()
        if email and email != voter.email:
            if User.query.filter_by(email=email).first():
                flash('Email already registered to another user.', 'warning')
                return redirect(url_for('admin.edit_voter', voter_id=voter.id))
            voter.email = email

        password = request.form.get('password', '').strip()
        if password:
            voter.set_password(password)

        voter.active = request.form.get('active') == 'on'
        db.session.commit()
        flash('Voter information updated.', 'success')
        return redirect(url_for('admin.manage_votes'))

    return render_template('admin_voter_form.html', user=user, page_title='Edit Voter', submit_label='Save Changes', voter=voter, form_action=url_for('admin.edit_voter', voter_id=voter.id))


@bp.route('/admin/manage_votes/<int:voter_id>/delete')
@login_required(role='admin')
def delete_voter(voter_id):
    voter = User.query.get_or_404(voter_id)
    Vote.query.filter_by(user_id=voter.id).delete()
    db.session.delete(voter)
    db.session.commit()
    flash('Voter deleted successfully.', 'success')
    return redirect(url_for('admin.manage_votes'))


@bp.route('/admin/manage_votes/<int:voter_id>/toggle_active')
@login_required(role='admin')
def toggle_voter_active(voter_id):
    voter = User.query.get_or_404(voter_id)
    voter.active = not voter.active
    db.session.commit()
    flash(f"Voter {'activated' if voter.active else 'deactivated'} successfully.", 'success')
    return redirect(url_for('admin.manage_votes'))


@bp.route('/admin/manage_votes/<int:voter_id>/reset_status')
@login_required(role='admin')
def reset_voter_status(voter_id):
    voter = User.query.get_or_404(voter_id)
    Vote.query.filter_by(user_id=voter.id).delete()
    db.session.commit()
    flash('Voter voting status has been reset.', 'success')
    return redirect(url_for('admin.manage_votes'))


@bp.route('/admin/reports')
@login_required(role='admin')
def reports():
    user = current_user()
    # placeholder: implement real report generation later
    return render_template('admin_reports.html', user=user)


@bp.route('/admin/audit_logs')
@login_required(role='admin')
def audit_logs():
    user = current_user()
    # placeholder: integrate with audit log model/system later
    logs = []
    return render_template('admin_audit_logs.html', user=user, logs=logs)


@bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required(role='admin')
def settings():
    user = current_user()
    settings = load_settings()
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'system':
            settings['system_name'] = request.form.get('system_name', '').strip() or 'Integrated School Portal'
            settings['theme'] = request.form.get('theme', 'dark') if request.form.get('theme') in ('dark', 'light') else 'dark'
            save_settings(settings)
            flash('System name and theme updated successfully.', 'success')
        elif form_type == 'logo':
            logo_file = request.files.get('logo')
            if logo_file and logo_file.filename and allowed_logo_filename(logo_file.filename):
                filename = secure_filename(logo_file.filename)
                save_path = STATIC_UPLOAD_DIR / filename
                logo_file.save(save_path)
                settings['logo_filename'] = filename
                save_settings(settings)
                flash('Logo uploaded successfully.', 'success')
            else:
                flash('Please upload a valid logo file (PNG, JPG, SVG, WEBP).', 'warning')
        elif form_type == 'rules':
            rules = settings.get('election_rules', {})
            try:
                rules['max_candidates_per_position'] = max(1, int(request.form.get('max_candidates_per_position', 8)))
            except ValueError:
                rules['max_candidates_per_position'] = 8
            rules['allow_write_ins'] = request.form.get('allow_write_ins') == 'on'
            rules['require_approval'] = request.form.get('require_approval') == 'on'
            settings['election_rules'] = rules
            save_settings(settings)
            flash('Election rules updated successfully.', 'success')
        elif form_type == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            if not user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'warning')
            else:
                user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        elif form_type == 'restore':
            upload_file = request.files.get('db_file')
            if upload_file and upload_file.filename.endswith('.db'):
                instance_db = Path(__file__).resolve().parent.parent / 'instance' / 'integrated_portal.db'
                temp_db = instance_db.with_suffix('.tmp.db')
                upload_file.save(temp_db)
                db.session.remove()
                db.engine.dispose()
                os.replace(temp_db, instance_db)
                flash('Database restored successfully. Restart server if needed.', 'success')
            else:
                flash('Please upload a valid SQLite .db file to restore.', 'warning')
        return redirect(url_for('admin.settings'))

    return render_template('admin_settings.html', user=user, settings=settings)


@bp.route('/admin/settings/backup')
@login_required(role='admin')
def backup_database():
    db_path = Path(__file__).resolve().parent.parent / 'instance' / 'integrated_portal.db'
    return send_file(str(db_path), as_attachment=True, download_name='integrated_portal_backup.db')
