--CREATE DATABASE dido;

DROP TABLE IF EXISTS jobs;

DROP TABLE IF EXISTS job_status;


CREATE TABLE Jobs(
    job_id TEXT NOT NULL, -- Type of id TBD
    import_service TEXT NOT NULL,
    import_token TEXT,
    import_url TEXT NOT NULL,
    export_service TEXT NOT NULL,
    export_token TEXT,
    export_url TEXT NOT NULL,
    file_elements INT DEFAULT 0,
    processed_elements INT DEFAULT 0,
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

