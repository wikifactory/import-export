import enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import db_string
import datetime

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
    exporting_succeded = "exporting_succeded"
    finished_successfully = "finished_successfully"
    cancelled = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)

    import_service = Column(String)
    import_token = Column(String)
    import_url = Column(String)

    export_service = Column(String)
    export_token = Column(String)
    export_url = Column(String)

    job_status = relationship("JobStatus", uselist=False, backref="jobs")


class JobStatus(Base):
    __tablename__ = "job_status"
    status_id = Column(Integer, primary_key=True)
    job_id = Column(String, ForeignKey("jobs.job_id"))
    job_status = Column(String)
    t = Column(DateTime, default=datetime.datetime.utcnow)


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

