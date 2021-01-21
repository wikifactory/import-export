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
    exporting = "exporting"
    exporting_error_authorization_required = "exporting_error_authorization_required"
    exporting_error_data_unreachable = "exporting_error_data_unreachable"
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

