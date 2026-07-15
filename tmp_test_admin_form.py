from app import app
from flask import render_template

with app.test_request_context():
    try:
        render_template('admin_election_form.html', page_title='Test', form_action='/', election=None, events=[], positions='', statuses=['draft', 'open', 'closed'], submit_label='Save')
        print('OK')
    except Exception as e:
        import traceback
        traceback.print_exc()