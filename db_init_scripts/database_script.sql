--CREATE DATABASE dido;

DROP TABLE IF EXISTS jobs;

DROP TABLE IF EXISTS job_status;


CREATE TYPE status_type AS ENUM('pending', 
'importing', 'import_error_authorization_required', 'import_error_data_not_found',
'exporting', 'export_error_authorization_required', 'export_error_data_not_found', 
'finished', 'cancelled');

CREATE TABLE Jobs(
    job_id TEXT NOT NULL, -- Type of id TBD
    import_service TEXT NOT NULL,
    import_token TEXT,
    import_url TEXT NOT NULL,
    export_service TEXT NOT NULL,
    export_token TEXT,
    export_url TEXT NOT NULL,
    --current_status TEXT NOT NULL,
    --status INT REFERENCES job_status(status_id),
    PRIMARY KEY (job_id)
);

CREATE TABLE job_status(
    status_id SERIAL,
    job_id TEXT NOT NULL,
    job_status TEXT,
    t TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (status_id),
    FOREIGN KEY (job_id) REFERENCES Jobs (job_id)
    ON DELETE CASCADE 
);