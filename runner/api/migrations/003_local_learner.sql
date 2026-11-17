CREATE TABLE learners(id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created REAL NOT NULL);
INSERT INTO learners VALUES ('local','Local learner',CAST(strftime('%s','now') AS REAL));
ALTER TABLE attempts ADD COLUMN learner_id TEXT NOT NULL DEFAULT 'local';
ALTER TABLE exams ADD COLUMN learner_id TEXT NOT NULL DEFAULT 'local';
