HOW TO USE THIS FOLDER
=======================
These are the 10 FINAL files that changed, with the same folder paths as your
repo (AI-Visual-scheduler/). Drop them into your local clone, overwriting the
existing files at those paths, then do the one manual step below, then commit.

FILES TO OVERWRITE (copy over the existing file at the same path):
  .env.example
  README.md
  app/agents/tools.py
  app/api/google.py
  app/db/models.py
  app/db/session.py
  app/services/calendar_service.py
  requirements.txt
  tests/test_app.py

ONE MANUAL STEP (rename, not overwrite):
  1. Delete your existing root-level app.py
  2. Add the included run_local.py in its place (same content as your old
     app.py, just renamed — this removes an ambiguity that could break
     Vercel's auto-detection of your FastAPI app, explained in chat)

THEN:
  git add -A
  git commit -m "Move DB to Postgres, fix Calendar token storage for Vercel"
  git push

WHAT CHANGED, IN ONE LINE EACH:
  requirements.txt        -> added psycopg2-binary (Postgres driver)
  app/db/session.py       -> added pool_pre_ping=True + a migration entry for the new column
  app/db/models.py        -> added google_token column on User
  app/services/calendar_service.py -> tokens now read/write to the DB column instead of a .pickle file
  app/api/google.py       -> passes the DB session through to the calendar functions above
  app/agents/tools.py     -> same, passes session through where the agent checks/uses Calendar
  run_local.py (new)      -> renamed from app.py, for the Vercel reason above
  README.md               -> updated the two mentions of app.py to run_local.py
  .env.example            -> added a Postgres URL example, removed the now-unused GOOGLE_TOKEN_DIR
  tests/test_app.py       -> removed one leftover line for the old file-based token system
