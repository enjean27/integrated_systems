import importlib.util

spec = importlib.util.spec_from_file_location('integrated_app', 'C:/Users/Admin/OneDrive/Desktop/integrated_systems/app.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

client = mod.app.test_client()
print('Testing Event System Login Flow\n')
print('=' * 60)

test_users = [
    ('admin@gmail.com', 'admin12345', 'Admin'),
    ('organizer@gmail.com', 'organizer12345', 'Organizer'),
    ('enjeangarcia236@gmail.com', 'user12345', 'User'),
]

for email, password, role in test_users:
    resp = client.post('/events/', data={'email': email, 'password': password}, follow_redirects=False)
    location = resp.headers.get('Location')
    status = resp.status_code
    print(f'{role:12} | Status: {status} | Redirect: {location}')
    
print('=' * 60)
print('\nDashboard access test:')
print('=' * 60)

dashboards = [
    ('/events/admin/dashboard', 'Admin Dashboard'),
    ('/events/organizer/dashboard', 'Organizer Dashboard'),
    ('/events/user/dashboard', 'User Dashboard'),
]

for path, name in dashboards:
    resp = client.get(path, follow_redirects=False)
    status = resp.status_code
    print(f'{name:25} | Status: {status}')

print('=' * 60)
