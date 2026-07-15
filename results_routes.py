import csv
import io
from flask import Blueprint, render_template, Response
from routes.auth_routes import login_required, current_user
from models import Election, Candidate, Vote, Position

bp = Blueprint('results', __name__, template_folder='../templates')


def _build_pdf(lines):
    header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
    objects = []

    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    content_lines = [b"BT /F1 14 Tf 40 760 Td\n"]
    for i, line in enumerate(lines):
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        content_lines.append(f"({escaped}) Tj\n".encode('latin1'))
        if i < len(lines) - 1:
            content_lines.append(b"0 -18 Td\n")
    content_stream = b"".join(content_lines)
    stream_obj = b"4 0 obj\n<< /Length %d >>\nstream\n" % len(content_stream)
    stream_obj += content_stream + b"endstream\nendobj\n"

    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n"
    )
    objects.append(stream_obj)
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    offsets = []
    current = len(header)
    for obj in objects:
        offsets.append(current)
        current += len(obj)

    body = header + b"".join(objects)
    xref = [b"xref\n0 %d\n" % (len(offsets) + 1), b"0000000000 65535 f \n"]
    for offset in offsets:
        xref.append(f"{offset:010d} 00000 n \n".encode('latin1'))
    xref_bytes = b"".join(xref)
    trailer = f"trailer\n<< /Size {len(offsets) + 1} /Root 1 0 R >>\nstartxref\n{len(body)}\n%%EOF\n".encode('latin1')
    return body + xref_bytes + trailer


def _build_results_data():
    elections = Election.query.order_by(Election.created_at.desc()).all()
    election_results = {}
    final_results = []
    position_winners = []
    vote_summary = []
    total_votes = 0
    total_candidates = 0

    for e in elections:
        cands = Candidate.query.filter_by(election_id=e.id).all()
        counts = []
        by_position = {}
        for c in cands:
            cnt = Vote.query.filter_by(election_id=e.id, choice=str(c.id)).count()
            counts.append({'candidate': c, 'votes': cnt})
            total_candidates += 1
            by_position.setdefault(c.position or 'Unspecified', []).append({'candidate': c, 'votes': cnt})

        total_election_votes = sum(item['votes'] for item in counts)
        total_votes += total_election_votes
        election_results[e.id] = sorted(counts, key=lambda x: x['votes'], reverse=True)

        if counts:
            winner = max(counts, key=lambda x: x['votes'])
            final_results.append(
                {
                    'election': e,
                    'winner': winner['candidate'],
                    'votes': winner['votes'],
                    'status': e.status,
                }
            )
        else:
            final_results.append(
                {
                    'election': e,
                    'winner': None,
                    'votes': 0,
                    'status': e.status,
                }
            )

        for position, items in by_position.items():
            winner = max(items, key=lambda x: x['votes'])
            position_winners.append(
                {
                    'election': e,
                    'position': position,
                    'candidate': winner['candidate'],
                    'votes': winner['votes'],
                }
            )

        vote_summary.append(
            {
                'election': e,
                'total_votes': total_election_votes,
                'candidate_count': len(cands),
                'status': e.status,
            }
        )

    return {
        'elections': elections,
        'election_results': election_results,
        'final_results': final_results,
        'position_winners': position_winners,
        'vote_summary': vote_summary,
        'live_vote_count': Vote.query.count(),
        'total_votes': total_votes,
        'total_candidates': total_candidates,
        'total_elections': len(elections),
    }


@bp.route('/elections/results')
@login_required()
def elections_results():
    user = current_user()
    context = _build_results_data()
    return render_template('results.html', user=user, **context)


@bp.route('/elections/results/export/csv')
@login_required()
def export_results_csv():
    data = _build_results_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Election Title', 'Status', 'Position', 'Candidate', 'Votes'])
    for election_id, items in data['election_results'].items():
        election = next((e for e in data['elections'] if e.id == election_id), None)
        for item in items:
            writer.writerow([
                election.title if election else 'Unknown Election',
                election.status if election else 'unknown',
                item['candidate'].position,
                item['candidate'].name,
                item['votes'],
            ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename="election_results.csv"'
    return response


@bp.route('/elections/results/export/pdf')
@login_required()
def export_results_pdf():
    data = _build_results_data()
    lines = [
        'Election Results Report',
        f'Live Vote Count: {data["live_vote_count"]}',
        f'Total Elections: {data["total_elections"]}',
        f'Total Candidates: {data["total_candidates"]}',
        '',
    ]
    for result in data['final_results']:
        winner_label = result['winner'].name if result['winner'] else 'No winner yet'
        lines.append(f'{result["election"].title} ({result["status"].capitalize()}): {winner_label} - {result["votes"]} votes')

    pdf_bytes = _build_pdf(lines)
    response = Response(pdf_bytes, mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename="election_results.pdf"'
    return response
