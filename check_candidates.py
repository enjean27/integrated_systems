from app import app
from models import Candidate, Election
from extensions import db

with app.app_context():
    print('=== DATABASE CHECK ===')
    candidates = Candidate.query.all()
    elections = Election.query.all()
    
    print(f'\nTotal Candidates: {len(candidates)}')
    print(f'Total Elections: {len(elections)}')
    
    print('\n--- Elections ---')
    for e in elections:
        print(f'ID: {e.id}, Title: {e.title}, Status: {e.status}')
    
    print('\n--- Candidates ---')
    for c in candidates:
        print(f'ID: {c.id}, Name: {c.name}, Position: {c.position}, Election ID: {c.election_id}')
    
    # Check if candidates are linked to elections
    print('\n--- Candidate-Election Links ---')
    for e in elections:
        linked_candidates = Candidate.query.filter_by(election_id=e.id).all()
        print(f'Election "{e.title}" (ID: {e.id}): {len(linked_candidates)} candidates')
        for c in linked_candidates:
            print(f'  - {c.name} ({c.position})')
