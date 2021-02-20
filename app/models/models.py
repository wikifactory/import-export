import datetime
import enum
import os
import sys
import urllib.parse

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    not_,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


# Create the connection with the DB here
class StatusEnum(enum.Enum):
    pending = "pending"
    importing = "importing"
    importing_error_authorization_required = "importing_error_authorization_required"
    importing_error_data_unreachable = "importing_error_data_unreachable"
    importing_successfully = "importing_successfully"
    exporting = "exporting"
    exporting_error_authorization_required = "exporting_error_authorization_required"
    exporting_error_data_unreachable = "exporting_error_data_unreachable"
    exporting_successfully = "exporting_successfully"
    finished_successfully = "finished_successfully"
    cancelled = "cancelled"

    retry = "retry"


status_list = []

for entry in StatusEnum:
    status_list.append(entry.value)

status_list = tuple(status_list)


status_types_enum = ENUM(*status_list, name="job_status")


class JobStatus(Base):
    __tablename__ = "job_statuses"
    status_id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"))
    status = Column(status_types_enum)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", uselist=False, backref="statuses")


def init_engine():
    root_engine = create_engine(os.environ["SQLALCHEMY_DATABASE_URI"])

    with root_engine.connect() as root_connection:
        dsn = os.environ[
            "POSTGRES_TEST_DSN" if "pytest" in sys.modules else "POSTGRES_DSN"
        ]
        database_name = urllib.parse.urlparse(dsn).path[1:]

        engine = create_engine(dsn)

        try:
            with engine.connect() as connection:
                connection.execute("SELECT 1")
        except OperationalError:
            root_connection.execute("COMMIT")
            root_connection.execute(f"CREATE DATABASE {database_name}")

        if not engine.table_names():
            Base.metadata.create_all(engine)

        return engine


Session = sessionmaker(bind=init_engine())


def add_job_to_db(options, job_id):

    session = Session()
    new_job = Job()
    new_job.job_id = job_id
    new_job.import_service = options["import_service"]
    new_job.import_token = options["import_token"]
    new_job.import_url = options["import_url"]

    new_job.export_service = options["export_service"]
    new_job.export_token = options["export_token"]
    new_job.export_url = options["export_url"]

    new_job.processed_elements = 0
    new_job.file_elements = 0

    new_status = JobStatus()
    new_status.job_id = new_job.job_id
    new_status.status = StatusEnum.pending.value

    session.add(new_job)
    session.add(new_status)
    session.commit()

    session.close()


def set_job_status(job_id, status: str):

    session = Session()
    new_status = JobStatus()
    new_status.job_id = job_id
    new_status.status = status

    session.add(new_status)
    session.commit()


def increment_processed_element_for_job(job_id):

    session = Session()
    # FIXME
    # Find the job and update
    for j in session.query(Job).filter(Job.job_id == job_id).all():
        j.processed_elements = j.processed_elements + 1

    session.commit()


def set_number_of_files_for_job_id(job_id, files):

    session = Session()

    # Find the job and update
    session.query(Job).filter(Job.job_id == job_id).update({"file_elements": files})

    session.commit()


"""
    The overall progress of the process is calculated taking into
    account the different steps through which the job has passed.
"""


def get_job_overall_progress(job_id):

    statuses_to_watch = [
        StatusEnum.pending.value,
        StatusEnum.importing.value,
        StatusEnum.importing_successfully.value,
        StatusEnum.exporting.value,
        StatusEnum.exporting_successfully.value,
    ]
    session = Session()

    count = (
        session.query(Job.job_id, JobStatus.status)
        .filter(Job.job_id == JobStatus.job_id, Job.job_id == job_id)
        .filter(
            Job.job_id == JobStatus.job_id,
            Job.job_id == job_id,
            JobStatus.status.in_(statuses_to_watch),
        )
        .count()
    )

    return count * (100.0 / len(statuses_to_watch))


# FIXME - replace get_job with this
def get_db_job(job_id):
    # FIXME - Use session per request
    session = Session()

    return session.query(Job).get(job_id)


# FIXME
def get_job(job_id):

    session = Session()

    result = (
        session.query(
            Job.job_id,
            JobStatus.status,
            Job.file_elements,
            Job.processed_elements,
        )
        .filter(Job.job_id == JobStatus.job_id, Job.job_id == job_id)
        .order_by(JobStatus.timestamp.desc())
        .limit(1)
        .all()
    )

    if len(result) == 0:
        return None

    result = result[0]

    if result[2] == 0:
        percentage = 0.0
    else:
        percentage = round((result[3] * 100.0) / result[2], 2)

    job_dict = {
        "job_id": str(result[0]),
        "job_status": result[1],
        "job_progress": percentage,
        "overall_process": get_job_overall_progress(job_id),
    }
    return job_dict


def get_unfinished_jobs():

    session = Session()
    result = (
        session.query(JobStatus.job_id, JobStatus.status)
        .order_by(JobStatus.timestamp.desc())
        .all()
    )

    jobs_dict = {}

    for row in result:
        if row[0] not in jobs_dict:
            jobs_dict[row[0]] = []
        jobs_dict[row[0]].append(row[1])

    unfinished = []

    for key_job in jobs_dict:
        if (
            StatusEnum.importing_successfully.value not in jobs_dict[key_job]
            or StatusEnum.exporting_successfully.value not in jobs_dict[key_job]
        ):
            unfinished.append(str(key_job))

    return {"unfinished_jobs": unfinished}


def get_jobs():
    session = Session()

    result = []

    for job_id, status in (
        session.query(JobStatus.job_id, JobStatus.status)
        .order_by(JobStatus.timestamp.desc())
        .all()
    ):
        result.append({"id": str(job_id), "status": status})

    return result


def import_export_job_combination_exists(import_url, export_url):

    session = Session()

    finished_job_statuses = [
        StatusEnum.cancelled.value,
        StatusEnum.exporting_successfully.value,
    ]

    exists = (
        session.query(Job)
        .filter(Job.import_url == import_url, Job.export_url == export_url)
        .filter(not_(Job.statuses.any(JobStatus.status.in_(finished_job_statuses))))
    ).exists()

    return session.query(exists).scalar()


def running_job_exists(job_id):

    session = Session()

    finished_job_statuses = [
        StatusEnum.cancelled.value,
        StatusEnum.exporting_successfully.value,
    ]

    exists = (
        session.query(Job)
        .filter(Job.job_id == job_id)
        .filter(not_(Job.statuses.any(JobStatus.status.in_(finished_job_statuses))))
    ).exists()

    return session.query(exists).scalar()


def cancel_job(job_id):
    session = Session()

    # Check if the job exists

    result = session.query(Job).get(job_id)

    if result is None:
        # We didn't find the job
        return {
            "error": "Job with id {} not found".format(job_id),
            "code": 404,
        }

    # Otherwise, we did find the job, but is it running at this moment?

    if running_job_exists(job_id):
        # We can cancell it
        set_job_status(job_id, StatusEnum.cancelled.value)
        return {"msg": "Job with id {} cancelled".format(job_id)}
    else:
        return {
            "error": "The job with id {} is not running and it can't be cancelled".format(
                job_id
            ),
            "code": 422,
        }


def can_retry_job(body: dict, job_id):
    session = Session()

    # Check if the job exists
    result = session.query(Job).get(job_id)

    if result is None:
        # We didn't find the job, so we cannot retry
        return {
            "error": "Job with id {} not found".format(job_id),
            "code": 404,
        }

    # If the job was found

    if not running_job_exists(job_id):
        # We can cancell it
        return {"msg": "job can be retried"}
    else:
        return {
            "error": "The job with id {} is not running and it can't be retried".format(
                job_id
            ),
            "code": 422,
        }


def set_retry_job(job_id):
    session = Session()

    # Check if the job exists
    result = session.query(Job).get(job_id)

    if result is None:
        # We didn't find the job
        return {"error": "Job with id {} not found".format(job_id)}

    # Otherwise, we did find the job, set the status to retry
    set_job_status(job_id, StatusEnum.retry.value)

    return {"msg": "Status of job {} changed to retry".format(job_id)}
