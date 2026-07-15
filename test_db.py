import sqlite3
import os

db_path = 'instance/integrated_portal.db'
print(f'Database path: {db_path}')
print(f'Database exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'\nTables in database: {len(tables)}')
    for table in tables:
        print(f'  - {table[0]}')
    
    # Check elections
    if any('election' in t[0].lower() for t in tables):
        cursor.execute("SELECT id, title, status FROM election")
        elections = cursor.fetchall()
        print(f'\nElections: {len(elections)}')
        for e in elections:
            print(f'  ID: {e[0]}, Title: {e[1]}, Status: {e[2]}')
    
    # Check candidates
    if any('candidate' in t[0].lower() for t in tables):
        cursor.execute("SELECT id, name, position, election_id FROM candidate")
        candidates = cursor.fetchall()
        print(f'\nCandidates: {len(candidates)}')
        for c in candidates:
            print(f'  ID: {c[0]}, Name: {c[1]}, Position: {c[2]}, Election ID: {c[3]}')
    
    conn.close()
else:
    print('Database file does not exist!')
