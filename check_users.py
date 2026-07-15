import sys
sys.path.insert(0, 'C:/Users/Admin/OneDrive/Desktop/GROUP14B_EVENT_MANAGEMENT_SYSTEM')
from db.connection import execute_query

test_emails = ['admin@gmail.com', 'organizer@gmail.com', 'enjeangarcia236@gmail.com']
print('Checking test user accounts:\n')
for email in test_emails:
    user = execute_query('SELECT * FROM users WHERE email = %s', (email,), fetch=True)
    if user:
        role = user[0].get('role', 'N/A')
        print(f'{email:30} -> role: {role}')
    else:
        print(f'{email:30} -> NOT FOUND')
