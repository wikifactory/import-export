--CREATE DATABASE dido;

DROP TABLE IF EXISTS jobs;

DROP TABLE IF EXISTS job_status;


CREATE TYPE j_status AS ENUM('pending', 
'importing', 'import_error_authorization_required', 'import_error_data_not_found',
'exporting', 'export_error_authorization_required', 'export_error_data_not_found', 
'finished', 'cancelled');

CREATE TABLE jobs(
    job_id INT PRIMARY KEY NOT NULL, -- Type of id TBD
    import_service TEXT NOT NULL,
    import_token TEXT,
    import_url TEXT NOT NULL,
    export_service TEXT NOT NULL,
    export_token TEXT,
    export_url TEXT NOT NULL
);

CREATE TABLE job_status(
    job_id INT REFERENCES jobs(job_id),
    job_status j_status
);