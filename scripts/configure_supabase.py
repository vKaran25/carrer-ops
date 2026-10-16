"""Create an empty versioned PostgreSQL schema, then explicitly activate it locally."""
import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate', action='store_true', help='Apply schema migrations and select Supabase mode in root .env')
    args = parser.parse_args()
    if not args.activate:
        parser.error('Activation is explicit: supply --activate when ready. No SQLite data is copied.')
    from app.config import get_settings
    from dotenv import set_key
    settings = get_settings()
    url = settings.supabase_database_url
    if not url or '[YOUR-PASSWORD]' in url or '[YOUR_PASSWORD]' in url:
        parser.error('Set SUPABASE_DATABASE_URL with the real pooler password in .env; do not paste it into chat.')
    if not settings.supabase_url or not settings.supabase_publishable_key:
        parser.error('Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY first.')
    url = re.sub(r'^postgres(?:ql)?://', 'postgresql+psycopg://', url)
    settings.model_copy(update={'auth_mode': 'supabase', 'database_url': url}).validate_runtime()
    # URLs never appear in Alembic logs or error output.
    from alembic import command
    from alembic.config import Config
    try:
        config = Config(str(ROOT / 'alembic.ini'))
        config.set_main_option('script_location', str(ROOT / 'migrations'))
        command.upgrade(config, 'head')
    except Exception:
        print('Schema setup failed. Check the session-pooler host, encoded password, SSL and project availability. Credentials are not printed.', file=sys.stderr)
        raise SystemExit(1) from None
    set_key(str(ROOT / '.env'), 'DATABASE_URL', url, quote_mode='always')
    set_key(str(ROOT / '.env'), 'AUTH_MODE', 'supabase')
    print('PostgreSQL selected with an empty versioned schema. SQLite data was not imported.')
    print('Restart FastAPI, add your verified email with scripts/beta_access.py invite EMAIL, and configure Supabase redirects/Google/SMTP.')


if __name__ == '__main__':
    main()
