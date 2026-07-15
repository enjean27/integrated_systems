from app import app, db
from models import User

with app.app_context():
    db.drop_all()
    db.create_all()
    user = User(
        student_id='TST001',
        name='Test User',
        email='test@example.com',
        course_year='CS 1st',
        role='student',
        is_verified=True,
    )
    user.set_password('Password123!')
    db.session.add(user)
    db.session.commit()

    client = app.test_client()
    response = client.post(
        '/login',
        data={'email': 'test@example.com', 'password': 'Password123!'},
        follow_redirects=False,
    )
    print('login status', response.status_code, response.headers.get('Location'))
    if response.status_code == 302:
        location = response.headers.get('Location')
        otp_response = client.get(location)
        print('otp page status', otp_response.status_code)
        print(otp_response.get_data(as_text=True)[:1000])
    else:
        print(response.get_data(as_text=True))
