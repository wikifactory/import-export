from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

Base = declarative_base()


class J_Status(Enum):

    cancelled = -1
    pending = 1
    importing = 2
    import_error_authorization_required = 3
    import_error_data_not_found = 4
    exporting = 5
    export_error_authorization_required = 6
    export_error_data_not_found = 7
    finished = 8


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True)

    import_service = Column(String)
    import_token = Column(String)
    import_url = Column(String)

    export_service = Column(String)
    export_token = Column(String)
    export_url = Column(String)

    job_status = relationship("Job", uselist=False, back_populates="jobs")


class JobStatus(Base):
    __tablename__ = "job_status"
    job_id = Column(Integer, ForeignKey("jobs.job_id"))
    job_status = Column(Enum(J_Status))
