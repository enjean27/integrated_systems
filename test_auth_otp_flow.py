import os
import unittest
from unittest.mock import patch

from app import app, db
from models import User


class OTPFlowTests(unittest.TestCase):
    def setUp(self):
        os.environ['SECRET_KEY'] = 'test-secret'
        self.app = app
        self.app.config['TESTING'] = True
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def test_register_redirects_to_otp_and_sends_to_entered_email(self):
        with self.app.test_client() as client:
            with patch('routes.auth_routes.send_otp_email') as send_mock:
                response = client.post(
                    '/register',
                    data={
                        'student_id': 'TEST001',
                        'full_name': 'Test User',
                        'email': 'test@example.com',
                        'course_year': 'BSCS 2nd Year',
                        'password': 'Password123!',
                        'confirm_password': 'Password123!',
                        'terms': 'on',
                    },
                    follow_redirects=False,
                )

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers['Location'].endswith('/otp'))
                send_mock.assert_called_once()
                self.assertEqual(send_mock.call_args.args[0], 'test@example.com')

                with self.app.app_context():
                    user = User.query.filter_by(email='test@example.com').first()
                    self.assertIsNotNone(user)
                    self.assertFalse(user.is_verified)

    def test_login_redirects_directly_to_dashboard_without_otp(self):
        with self.app.app_context():
            user = User(
                student_id='STUDENT002',
                name='Login User',
                email='login@example.com',
                course_year='BSCS 2nd Year',
                role='student',
                is_verified=True,
            )
            user.set_password('Password123!')
            db.session.add(user)
            db.session.commit()

        with self.app.test_client() as client:
            with patch('routes.auth_routes.send_otp_email') as send_mock:
                response = client.post(
                    '/login',
                    data={
                        'email': 'login@example.com',
                        'password': 'Password123!',
                    },
                    follow_redirects=False,
                )

                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers['Location'].endswith('/dashboard'))
                send_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
