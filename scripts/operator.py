"""Server-side beta admission and setup; no message is sent to invited addresses."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlmodel import Session, select
from app.config import get_settings
from app.db import make_engine
from app.models import Invitation, SearchRun, User, utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['invite', 'revoke', 'list'])
    parser.add_argument('emails', nargs='*')
    args = parser.parse_args()
    settings = get_settings()
    url = settings.supabase_database_url or settings.database_url
    if not url.startswith(('postgresql', 'postgres://')):
        parser.error('Configure SUPABASE_DATABASE_URL first; invitations belong to PostgreSQL.')
    if args.action != 'list' and (not args.emails or any('@' not in email or len(email)>320 for email in args.emails)):
        parser.error('Supply one or more valid invited email addresses.')
    engine = make_engine(url)
    try:
        with Session(engine) as session:
            if args.action == 'list':
                for row in session.exec(select(Invitation).order_by(Invitation.email)).all():
                    print(row.email + ': ' + ('enabled' if row.enabled else 'revoked'))
                return
            for supplied in dict.fromkeys(args.emails):
                email = supplied.strip().casefold()
                row = session.get(Invitation, email) or Invitation(email=email)
                row.enabled, row.updated_at = args.action == 'invite', utcnow()
                session.add(row)
                if not row.enabled:
                    users = session.exec(select(User.id).where(User.email == email)).all()
                    for run in session.exec(select(SearchRun).where(SearchRun.user_id.in_(users),
                                                 SearchRun.status.in_(['queued', 'running', 'cancelling']))).all():
                        run.cancel_requested = True
                        run.status = 'cancelled' if run.status == 'queued' else 'cancelling'
                        session.add(run)
            session.commit()
            print('Invitations enabled. No email was sent.' if args.action=='invite' else 'Access revoked and unfinished searches cancelled.')
    except Exception:
        print('Operator action failed. Check database setup and connectivity; credentials are not printed.', file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
