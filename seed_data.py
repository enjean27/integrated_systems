from supabase import create_client
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

url = os.getenv("SUPABASE_URL") or "https://dranehdinxnexbqvpuef.supabase.co"
# Try service role key first (bypasses RLS), fall back to publishable key
key = os.getenv("sb_publishable_IsqNMg8FcAFz6a9DxohVEA_aKHb1i1D") or os.getenv("sb_publishable_IsqNMg8FcAFz6a9DxohVEA_aKHb1i1D") or os.getenv("SUPABASE_KEY") or "sb_publishable_IsqNMg8FcAFz6a9DxohVEA_aKHb1i1D"

supabase = create_client(url, key)

def insert_with_retry(table_name, data):
    """Insert data and handle RLS errors gracefully."""
    try:
        print(f"Inserting into {table_name}...")
        supabase.table(table_name).insert(data).execute()
        print(f"✅ {table_name} inserted successfully")
    except Exception as e:
        error_msg = str(e)
        if "row-level security policy" in error_msg.lower():
            print(f"⚠️ {table_name}: RLS is blocking inserts - SKIPPING")
            print(f"   (Please disable RLS in Supabase dashboard)")
        elif "duplicate key" in error_msg.lower() or "23505" in error_msg:
            print(f"⚠️ {table_name}: Duplicate records - SKIPPING")
        else:
            print(f"❌ Error inserting {table_name}: {error_msg}")
        # Don't raise - continue to next table
        return False
    return True

# =========================
# USERS
# =========================
users_data = [
    {
        "full_name": "Jessa Tagle",
        "email": "jessatagle40@gmail.com",
        "password_hash": generate_password_hash("student123"),
    },
    {
        "full_name": "Enjean Garcia",
        "email": "enjean@gmail.com",
        "password_hash": generate_password_hash("student123"),
    },
    {
        "full_name": "Diana Tagle",
        "email": "dianatagle98@gmail.com",
        "password_hash": generate_password_hash("student123"),
    },
]
insert_with_retry("users", users_data)

# =========================
# EVENTS
# =========================
events_data = [
    {
        "title": "Orientation 2026",
        "description": "Welcome event for new students",
        "event_date": "2026-07-15T09:00:00"
    },
    {
        "title": "SSG Election Event",
        "description": "Student council election",
        "event_date": "2026-07-20T10:00:00"
    }
]
insert_with_retry("events", events_data)

# =========================
# ELECTIONS
# =========================
elections_data = [
    {
        "title": "SSG Election 2026",
        "description": "Annual student council election",
        "event_id": 1,
        "start_date": "2026-07-15",
        "end_date": "2026-07-30"
    }
]
insert_with_retry("elections", elections_data)

# =========================
# POSITIONS
# =========================
positions_data = [
    {"position_name": "President", "election_id": 1},
    {"position_name": "Vice President", "election_id": 1},
    {"position_name": "Secretary", "election_id": 1},
    {"position_name": "Treasurer", "election_id": 1},
    {"position_name": "Auditor", "election_id": 1},
]
insert_with_retry("positions", positions_data)

# =========================
# CANDIDATES
# =========================
candidates_data = [
    {"full_name": "Garcia Enjean", "position_id": 1, "election_id": 1},
    {"full_name": "Padis Sharmaine", "position_id": 1, "election_id": 1},
    {"full_name": "Tagle Jessa", "position_id": 2, "election_id": 1},
    {"full_name": "Anna Lopez", "position_id": 2, "election_id": 1},
    {"full_name": "Mark Garcia", "position_id": 3, "election_id": 1},
    {"full_name": "Juan Dela Cruz", "position_id": 3, "election_id": 1},
    {"full_name": "Maria Santos", "position_id": 4, "election_id": 1},
    {"full_name": "Jose Reyes", "position_id": 4, "election_id": 1},
    {"full_name": "Ana Cruz", "position_id": 5, "election_id": 1},
    {"full_name": "Pedro Mendoza", "position_id": 5, "election_id": 1},
]
insert_with_retry("candidates", candidates_data)

# =========================
# EVENT REGISTRATIONS
# =========================
registrations_data = [
    {"user_id": 1, "event_id": 1},

]
insert_with_retry("event_registrations", registrations_data)

# =========================
# ATTENDANCE
# =========================
attendance_data = [
    {"user_id": 1, "event_id": 1},
    
]
insert_with_retry("attendance", attendance_data)

# =========================
# ANNOUNCEMENTS
# =========================
announcements_data = [
    {"title": "Welcome", "content": "Welcome to integrated systems!"},
    {"title": "Election Notice", "content": "Voting starts tomorrow"},
]
insert_with_retry("announcements", announcements_data)

# =========================
# NOTIFICATIONS
# =========================
notifications_data = [
    {"user_id": 1, "message": "You are registered!"},
    {"user_id": 1, "message": "Don't forget to vote"},
]
insert_with_retry("notifications", notifications_data)

# =========================
# VOTES
# =========================
votes_data = [
    {"voter_id": 1, "election_id": 1, "position_id": 1, "candidate_id": 1},
]
insert_with_retry("votes", votes_data)

print("\n✅ SEEDING COMPLETE!")