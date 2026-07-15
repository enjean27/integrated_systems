from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import Election, Vote, Candidate, Position
from extensions import db
from routes.auth_routes import login_required, current_user

bp = Blueprint('voting', __name__, template_folder='../templates')


@bp.route('/voting')
@login_required()
def index():
    user = current_user()
    elections = Election.query.order_by(Election.created_at.desc()).all()
    active = [e for e in elections if e.status == 'active']
    closed = [e for e in elections if e.status != 'active']
    return render_template('voting.html', active_elections=active, closed_elections=closed, user=user)


# aliases to match required URL structure
@bp.route('/elections')
@login_required()
def elections_alias():
    return index()


@bp.route('/elections/vote/<int:election_id>')
@login_required()
def elections_vote(election_id):
    return ballot(election_id)


@bp.route('/elections/results')
@login_required()
def elections_results_alias():
    return redirect(url_for('results.elections_results'))


@bp.route('/voting/elections')
@login_required()
def elections():
    user = current_user()
    elections = Election.query.order_by(Election.created_at.desc()).all()
    return render_template('elections.html', elections=elections, user=user)


@bp.route('/voting/ballot/<int:election_id>', methods=['GET', 'POST'])
@login_required()
def ballot(election_id):
    user = current_user()
    election = Election.query.get_or_404(election_id)
    existing_vote = Vote.query.filter_by(user_id=user.id, election_id=election.id).first()
    candidates = Candidate.query.filter_by(election_id=election.id).order_by(Candidate.created_at.asc()).all()
    positions = Position.query.filter_by(election_id=election.id).order_by(Position.created_at.asc()).all()
    
    # Debug: Print candidate info
    print(f"DEBUG: Election ID: {election_id}, Election Title: {election.title}")
    print(f"DEBUG: Candidates found: {len(candidates)}")
    for c in candidates:
        print(f"DEBUG: Candidate - ID: {c.id}, Name: {c.name}, Position: {c.position}")
    
    if request.method == 'POST':
        choice = request.form.get('choice', '').strip()
        if existing_vote:
            flash('You have already voted in this election.', 'info')
            return redirect(url_for('voting.ballot', election_id=election.id))
        if not choice:
            flash('Please choose a candidate.', 'warning')
            return redirect(url_for('voting.ballot', election_id=election.id))
        db.session.add(Vote(election_id=election.id, user_id=user.id, choice=choice))
        db.session.commit()
        flash('Your vote has been recorded.', 'success')
        return redirect(url_for('voting.results'))

    return render_template('ballot.html', election=election, candidates=candidates, positions=positions, existing_vote=existing_vote, user=user)


@bp.route('/voting/results')
@login_required()
def results():
    user = current_user()
    elections = Election.query.order_by(Election.created_at.desc()).all()

    final_results = []
    position_winners = []
    vote_summary = []
    total_votes = 0
    total_candidates = 0

    for e in elections:
        cands = Candidate.query.filter_by(election_id=e.id).all()
        counts = []
        for c in cands:
            cnt = Vote.query.filter_by(election_id=e.id, choice=str(c.id)).count()
            counts.append({'candidate': c, 'votes': cnt})
            total_candidates += 1

        election_total_votes = sum(item['votes'] for item in counts)
        total_votes += election_total_votes

        if counts:
            winner = max(counts, key=lambda x: x['votes'])
            final_results.append({
                'election': e,
                'winner': winner['candidate'],
                'votes': winner['votes'],
                'status': e.status,
            })
        else:
            final_results.append({
                'election': e,
                'winner': None,
                'votes': 0,
                'status': e.status,
            })

        by_position = {}
        for c in cands:
            by_position.setdefault(c.position or 'Candidate', []).append({'candidate': c, 'votes': next((item['votes'] for item in counts if item['candidate'].id == c.id), 0)})

        for position, items in by_position.items():
            winner = max(items, key=lambda x: x['votes'])
            position_winners.append({
                'election': e,
                'position': position,
                'candidate': winner['candidate'],
                'votes': winner['votes'],
            })

        vote_summary.append({
            'election': e,
            'total_votes': election_total_votes,
            'candidate_count': len(cands),
            'status': e.status,
        })

    context = {
        'user': user,
        'elections': elections,
        'final_results': final_results,
        'position_winners': position_winners,
        'vote_summary': vote_summary,
        'live_vote_count': Vote.query.count(),
        'total_votes': total_votes,
        'total_candidates': total_candidates,
        'total_elections': len(elections),
    }

    return render_template('results.html', **context)


@bp.route('/voting/history')
@login_required()
def history():
    user = current_user()
    votes = Vote.query.filter_by(user_id=user.id).order_by(Vote.created_at.desc()).all()
    # attach candidate info when possible
    enriched = []
    for v in votes:
        cand = None
        try:
            cand = Candidate.query.get(int(v.choice)) if v.choice and v.choice.isdigit() else None
        except Exception:
            cand = None
        enriched.append({'vote': v, 'candidate': cand})
    return render_template('voting_history.html', votes=enriched, user=user)


@bp.route('/voting/dashboard')
@login_required()
def voter_dashboard():
    user = current_user()
    return render_template('voter_dashboard.html', user=user)
