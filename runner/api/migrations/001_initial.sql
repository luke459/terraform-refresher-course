CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES (1);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(
 id TEXT PRIMARY KEY, domain_id TEXT NOT NULL, account TEXT NOT NULL, region TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'active', created REAL NOT NULL, config_hash TEXT,
 verified_hash TEXT, baseline TEXT NOT NULL DEFAULT '{}', results TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id), operation TEXT NOT NULL,
 params TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, started REAL, finished REAL,
 exit_code INTEGER, config_hash TEXT, plan_hash TEXT, log TEXT NOT NULL DEFAULT '', result TEXT
);
CREATE INDEX IF NOT EXISTS jobs_attempt ON jobs(attempt_id,created);
CREATE TABLE IF NOT EXISTS resources(
 attempt_id TEXT NOT NULL REFERENCES attempts(id), address TEXT NOT NULL, type TEXT NOT NULL,
 resource_id TEXT NOT NULL, region TEXT NOT NULL, arn TEXT, tags TEXT NOT NULL DEFAULT '{}',
 status TEXT NOT NULL DEFAULT 'present', ownership_verified INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(attempt_id,address,resource_id)
);
CREATE TABLE IF NOT EXISTS exams(
 id TEXT PRIMARY KEY, mode TEXT NOT NULL, created REAL NOT NULL, deadline REAL,
 submitted REAL, question_ids TEXT NOT NULL, answers TEXT NOT NULL DEFAULT '{}', score REAL
);
CREATE TABLE IF NOT EXISTS checkpoints(
 domain_id TEXT NOT NULL, question_id TEXT NOT NULL, selected TEXT NOT NULL,
 correct INTEGER NOT NULL, updated REAL NOT NULL, PRIMARY KEY(domain_id,question_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS jobs_active_attempt ON jobs(attempt_id) WHERE status IN ('queued','running');
