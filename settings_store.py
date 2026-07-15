import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = INSTANCE_DIR / 'settings.json'
STATIC_UPLOAD_DIR = BASE_DIR / 'static' / 'uploads'
STATIC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    'system_name': 'Integrated School Portal',
    'logo_filename': None,
    'theme': 'dark',
    'election_rules': {
        'max_candidates_per_position': 8,
        'allow_write_ins': False,
        'require_approval': False,
    },
}


def load_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with SETTINGS_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: data.get(k, v) for k, v in DEFAULT_SETTINGS.items()})
        merged['election_rules'] = {**DEFAULT_SETTINGS['election_rules'], **data.get('election_rules', {})}
        return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    if settings is None:
        settings = DEFAULT_SETTINGS.copy()
    if 'election_rules' not in settings:
        settings['election_rules'] = DEFAULT_SETTINGS['election_rules'].copy()
    with SETTINGS_FILE.open('w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    return settings
