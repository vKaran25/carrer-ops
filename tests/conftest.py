"""Keep ordinary fixture tests off the configured production account store."""
import os
from pathlib import Path
import tempfile

# Applied before test modules import the application. Live PostgreSQL acceptance
# uses its own opt-in script and private test schema.
os.environ['AUTH_MODE'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(tempfile.mkdtemp(prefix='career-ops-fixtures-')) / 'workspace.db')
