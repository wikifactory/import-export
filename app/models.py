from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import db_string
import datetime
from sqlalchemy.dialects.postgresql import ENUM
import enum

engine = create_engine(db_string)

Session = sessionmaker(bind=engine)

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


status_list = []

for entry in StatusEnum:
    status_list.append(entry.value)

status_list = tuple(status_list)


status_types_enum = ENUM(*status_list, name="job_status")


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True)

    import_service = Column(String)
    import_token = Column(String)
    import_url = Column(String)

    export_service = Column(String)
    export_token = Column(String)
    export_url = Column(String)

    file_elements = Column(Integer)
    processed_elements = Column(Integer)

    job_status = relationship("JobStatus", uselist=False, backref="jobs")


class JobStatus(Base):
    __tablename__ = "job_status"
    status_id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"))
    job_status = Column(status_types_enum)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


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
    new_status.job_status = StatusEnum.pending.value

    session.add(new_job)
    session.add(new_status)
    session.commit()


def set_job_status(job_id, status: str):

    session = Session()
    new_status = JobStatus()
    new_status.job_id = job_id
    new_status.job_status = status

    session.add(new_status)
    session.commit()


def increment_processed_element_for_job(job_id):
    session = Session()
    # Find the job and update
    for j in session.query(Job).filter(Job.job_id == job_id).all():
        j.processed_elements = j.processed_elements + 1

    session.commit()


def set_number_of_files_for_job_id(job_id, files):
    session = Session()

    # Find the job and update
    session.query(Job).filter(Job.job_id == job_id).update({"file_elements": files})

    session.commit()


def get_job(job_id):
    session = Session()

    result = (
        session.query(
            Job.job_id,
            Job.import_service,
            Job.export_service,
            Job.import_url,
            Job.export_url,
            JobStatus.job_status,
            JobStatus.timestamp,
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

    if result[7] == 0:
        percentage = 0.0
    else:
        percentage = round((result[8] * 100.0) / result[7], 2)

    job_dict = {
        "job_id": result[0],
        "import_service": result[1],
        "export_service": result[2],
        "import_url": result[3],
        "export_url": result[4],
        "job_status": result[5],
        "timestamp": result[6],
        "job_progress": percentage,
    }
    return job_dict
