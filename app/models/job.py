import enum

from sqlalchemy import Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class JobStatus(enum.Enum):
    PENDING = 1
    IMPORTING = 2
    IMPORTING_ERROR_AUTHORIZATION_REQUIRED = 3
    IMPORTING_ERROR_DATA_UNREACHABLE = 4
    IMPORTING_SUCCESSFULLY = 5
    EXPORTING = 6
    EXPORTING_ERROR_AUTHORIZATION_REQUIRED = 7
    EXPORTING_ERROR_DATA_UNREACHABLE = 8
    EXPORTING_SUCCESSFULLY = 9
    FINISHED_SUCCESSFULLY = 10
    CANCELLING = 11
    CANCELLED = 12


terminated_job_statuses = [
    JobStatus.FINISHED_SUCCESSFULLY,
    JobStatus.CANCELLING,
    JobStatus.CANCELLED,
]


class Job(Base):
    __tablename__ = "job"

    id = Column(UUID(as_uuid=True), primary_key=True)

    import_service = Column(String)
    import_token = Column(String)
    import_url = Column(String)

    export_service = Column(String)
    export_token = Column(String)
    export_url = Column(String)

    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)

    path = Column(String)


class JobDuplicated(Exception):
    pass


class JobNotCancellable(Exception):
    pass


class JobNotRetriable(Exception):
    pass
