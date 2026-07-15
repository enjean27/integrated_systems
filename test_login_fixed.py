import importlib.util
from werkzeug.test import Client as WerkzeugClient

spec = importlib.util.spec_from_file_location('integrated_app', 'C:/Users/Admin/OneDrive/Desktop/integrated_systems/app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

app = mod.app
# Enable session support in test client
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

print('Testing Event System Login Flow with Session Support\n')
print('=' * 70)

test_users = [
    ('admin@gmail.com', 'admin12345', 'Admin'),
    ('organizer@gmail.com', 'organizer12345', 'Organizer'),
    ('enjeangarcia236@gmail.com', 'user12345', 'Participant/User'),
]

for email, password, role in test_users:
    with app.test_client() as client:
        # Login
        resp = client.post('/events/', data={'email': email, 'password': password}, follow_redirects=False)
        location = resp.headers.get('Location')
        status = resp.status_code
        
        # Check if we can access the dashboard
        if location:
            dashboard_resp = client.get(location, follow_redirects=False)
            dashboard_status = dashboard_resp.status_code
            print(f'{role:20} | Login: {status} -> {location:30} | Dashboard Access: {dashboard_status}')
        else:
            print(f'{role:20} | Login: {status} | NO REDIRECT')
    
print('=' * 70)
