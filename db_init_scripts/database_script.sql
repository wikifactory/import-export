CREATE EXTENSION IF NOT EXISTS dblink;

DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_database WHERE datname = 'dido') THEN
      RAISE NOTICE 'Database already exists';  -- optional
   ELSE
      PERFORM dblink_exec('dbname=' || current_database()  -- current db
                        , 'CREATE DATABASE dido');
   END IF;
END
$do$;

DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_database WHERE datname = 'test') THEN
      RAISE NOTICE 'Database already exists';  -- optional
   ELSE
      PERFORM dblink_exec('dbname=' || current_database()  -- current db
                        , 'CREATE DATABASE test');
   END IF;
END
$do$;




DROP TABLE IF EXISTS jobs;

DROP TABLE IF EXISTS job_status;

CREATE TYPE status_type AS ENUM (
    'pending',
    'importing',
    'importing_error_authorization_required',
    'importing_error_data_unreachable',
    'importing_successfully',
    'exporting',
    'exporting_error_authorization_required',
    'exporting_error_data_unreachable',
    'exporting_successfully',
    'finished_successfully',
    'cancelled'
);


CREATE TABLE Jobs(
    job_id UUID NOT NULL, -- Type of id TBD
    import_service TEXT NOT NULL,
    import_token TEXT,
    import_url TEXT NOT NULL,
    export_service TEXT NOT NULL,
    export_token TEXT,
    export_url TEXT NOT NULL,
    file_elements INT DEFAULT 0,
    processed_elements INT DEFAULT 0,
    PRIMARY KEY (job_id)
);

CREATE TABLE job_status(
    status_id SERIAL,
    job_id UUID NOT NULL,
    job_status status_type,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (status_id),
    FOREIGN KEY (job_id) REFERENCES Jobs (job_id)
    ON DELETE CASCADE 
);

CREATE INDEX idx_jobs_jobid ON Jobs(job_id);
CREATE INDEX idx_jobsstatus_job_id ON job_status(job_id);

ALTER TABLE Jobs ADD CONSTRAINT positive_number CHECK (file_elements >= 0 AND processed_elements >= 0)