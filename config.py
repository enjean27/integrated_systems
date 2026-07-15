import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from supabase import create_client
except ImportError:  # pragma: no cover - optional dependency in local/dev setups
    create_client = None

BASE_DIR = Path(__file__).resolve().parent
DOTENV_PATH = BASE_DIR / 'integrated_systems' / '.env'

if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = None
if SUPABASE_URL and SUPABASE_KEY and create_client:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mail configuration for OTP
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = "jessatagle681@gmail.com"
MAIL_PASSWORD = "rnii uxsv pdfm mwgs"

 
def get_supabase_client():
    """Return a Supabase client instance."""
    return supabase