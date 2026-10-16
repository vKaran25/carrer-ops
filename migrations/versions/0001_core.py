"""Frozen initial PostgreSQL core schema. No SQLite data is imported.

Future schema changes require a new revision. Statements are executed separately.
"""
from alembic import op

revision = '0001_core'
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = (
    """CREATE TABLE dailyusage (
	id SERIAL NOT NULL, 
	scope VARCHAR NOT NULL, 
	day VARCHAR NOT NULL, 
	operation VARCHAR NOT NULL, 
	count INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (scope, day, operation)
);""",
    """ALTER TABLE dailyusage ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE deletionrequest (
	subject VARCHAR(36) NOT NULL, 
	artifact_ids JSON, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (subject)
);""",
    """ALTER TABLE deletionrequest ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE discoverycache (
	key VARCHAR(64) NOT NULL, 
	results JSON, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);""",
    """CREATE INDEX ix_discoverycache_expires_at ON discoverycache (expires_at);""",
    """ALTER TABLE discoverycache ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE evalrun (
	id SERIAL NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	test_case_id VARCHAR NOT NULL, 
	score FLOAT NOT NULL, 
	notes VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);""",
    """ALTER TABLE evalrun ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE interviewresearchcache (
	id SERIAL NOT NULL, 
	company VARCHAR NOT NULL, 
	result JSON, 
	researched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);""",
    """CREATE UNIQUE INDEX ix_interviewresearchcache_company ON interviewresearchcache (company);""",
    """ALTER TABLE interviewresearchcache ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE invitation (
	email VARCHAR(320) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (email)
);""",
    """ALTER TABLE invitation ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE "user" (
	id SERIAL NOT NULL, 
	email VARCHAR, 
	auth_provider VARCHAR NOT NULL, 
	tier VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);""",
    """ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE workerheartbeat (
	id INTEGER NOT NULL, 
	worker_id VARCHAR NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);""",
    """ALTER TABLE workerheartbeat ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE authidentity (
	subject VARCHAR(36) NOT NULL, 
	user_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (subject), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE authidentity ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE chatturn (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	query VARCHAR NOT NULL, 
	mode VARCHAR NOT NULL, 
	resume_filename VARCHAR, 
	resume_digest VARCHAR, 
	result JSON, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """CREATE INDEX ix_chatturn_user_id ON chatturn (user_id);""",
    """ALTER TABLE chatturn ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE jobposting (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	company VARCHAR NOT NULL, 
	location VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	snippet VARCHAR NOT NULL, 
	description VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	found_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	posted_at TIMESTAMP WITH TIME ZONE, 
	source_metadata JSON, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, url), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """CREATE INDEX ix_jobposting_user_id ON jobposting (user_id);""",
    """ALTER TABLE jobposting ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE memoryfact (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	fact_text VARCHAR NOT NULL, 
	fact_type VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	source_key VARCHAR NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, source, source_key), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """CREATE INDEX ix_memoryfact_user_id ON memoryfact (user_id);""",
    """ALTER TABLE memoryfact ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE personalizationconsent (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE personalizationconsent ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE resumeprofile (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	filename VARCHAR NOT NULL, 
	raw_resume_text VARCHAR NOT NULL, 
	latex_source VARCHAR, 
	structured_facts JSON, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE resumeprofile ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE scoringweights (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	weights JSON, 
	last_recalibrated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	outcome_count INTEGER NOT NULL, 
	training_digest VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE scoringweights ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE searchcontext (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	intent JSON, 
	cleared_fields JSON, 
	query VARCHAR NOT NULL, 
	resume_digest VARCHAR, 
	last_turn_id INTEGER, 
	revision INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE searchcontext ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE searchpreferences (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	query VARCHAR NOT NULL, 
	spec JSON, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """ALTER TABLE searchpreferences ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE searchrun (
	id VARCHAR(32) NOT NULL, 
	user_id INTEGER NOT NULL, 
	request_key VARCHAR(64) NOT NULL, 
	request JSON, 
	status VARCHAR NOT NULL, 
	phase VARCHAR NOT NULL, 
	attempt INTEGER NOT NULL, 
	cancel_requested BOOLEAN NOT NULL, 
	worker_id VARCHAR, 
	heartbeat_at TIMESTAMP WITH TIME ZONE, 
	result JSON, 
	error VARCHAR, 
	resume_digest VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id, request_key), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);""",
    """CREATE INDEX ix_searchrun_status ON searchrun (status);""",
    """CREATE INDEX ix_searchrun_user_id ON searchrun (user_id);""",
    """ALTER TABLE searchrun ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE application (
	id SERIAL NOT NULL, 
	job_id INTEGER NOT NULL, 
	status VARCHAR NOT NULL, 
	tailored_resume VARCHAR, 
	tailored_cover_letter VARCHAR, 
	draft JSON, 
	critique JSON, 
	curated_resume JSON, 
	fit_score FLOAT, 
	explanation VARCHAR NOT NULL, 
	scoring_signals JSON, 
	applied_at TIMESTAMP WITH TIME ZONE, 
	outcome VARCHAR, 
	outcome_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (job_id), 
	FOREIGN KEY(job_id) REFERENCES jobposting (id)
);""",
    """ALTER TABLE application ENABLE ROW LEVEL SECURITY;""",
    """CREATE TABLE useraction (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	application_id INTEGER NOT NULL, 
	action VARCHAR NOT NULL, 
	previous_status VARCHAR NOT NULL, 
	new_status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(application_id) REFERENCES application (id)
);""",
    """ALTER TABLE useraction ENABLE ROW LEVEL SECURITY;""",
    """CREATE FUNCTION guard_applied_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'INSERT' THEN
  IF NEW.status = 'applied' OR NEW.applied_at IS NOT NULL THEN
   RAISE EXCEPTION 'Applied requires an explicit audited transition';
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.status = 'applied' AND NEW.applied_at IS NULL THEN
  RAISE EXCEPTION 'Applied status requires an audited timestamp';
 END IF;
 IF OLD.applied_at IS NOT NULL AND NEW.applied_at IS DISTINCT FROM OLD.applied_at THEN
  RAISE EXCEPTION 'Applied audit timestamp is immutable';
 END IF;
 IF NEW.status = 'applied' AND OLD.status <> 'applied' THEN
  IF NOT EXISTS (
   SELECT 1 FROM useraction a JOIN jobposting j ON j.id=NEW.job_id
   WHERE a.application_id=NEW.id AND a.user_id=j.user_id
    AND a.action='mark_applied' AND a.previous_status=OLD.status AND a.new_status='applied'
    AND a.xmin::text::bigint = (txid_current() % 4294967296)
  ) THEN RAISE EXCEPTION 'Applied requires a same-transaction user action'; END IF;
 END IF;
 IF OLD.applied_at IS NULL AND NEW.applied_at IS NOT NULL AND NEW.status <> 'applied' THEN
  RAISE EXCEPTION 'Applied timestamp requires explicit applied transition';
 END IF;
 RETURN NEW;
END $$;""",
    """CREATE TRIGGER applied_audit_guard BEFORE INSERT OR UPDATE ON application
 FOR EACH ROW EXECUTE FUNCTION guard_applied_transition();""",
    """CREATE FUNCTION guard_action_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM application a JOIN jobposting j ON j.id=a.job_id
                WHERE a.id=NEW.application_id AND j.user_id=NEW.user_id) THEN
  RAISE EXCEPTION 'Audit actor must own the application';
 END IF;
 RETURN NEW;
END $$;""",
    """CREATE TRIGGER audit_actor_guard BEFORE INSERT OR UPDATE ON useraction
 FOR EACH ROW EXECUTE FUNCTION guard_action_owner();""",
    """CREATE UNIQUE INDEX one_active_search_per_user ON searchrun(user_id)
 WHERE status IN ('queued','running','cancelling');""",
    """ALTER TABLE application ADD CONSTRAINT application_core_status
 CHECK (status IN ('interested','applied','interviewing','resolved','dismissed'));""",
    """ALTER TABLE searchrun ADD CONSTRAINT search_run_status
 CHECK (status IN ('queued','running','cancelling','succeeded','failed','cancelled','interrupted','needs_input'));""",
    """ALTER TABLE dailyusage ADD CONSTRAINT usage_nonnegative CHECK (count >= 0);""",
 )


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError('Destructive downgrade is disabled. Use a reviewed forward migration.')
