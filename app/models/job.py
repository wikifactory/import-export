import enum

from sqlalchemy import Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class JobStatus(enum.Enum):
    PENDING = "pending"
    IMPORTING = "importing"
    IMPORTING_ERROR_AUTHORIZATION_REQUIRED = "importing_error_authorization_required"
    IMPORTING_ERROR_DATA_UNREACHABLE = "importing_error_data_unreachable"
    IMPORTING_SUCCESSFULLY = "importing_successfully"
    EXPORTING = "exporting"
    EXPORTING_ERROR_AUTHORIZATION_REQUIRED = "exporting_error_authorization_required"
    EXPORTING_ERROR_DATA_UNREACHABLE = "exporting_error_data_unreachable"
    EXPORTING_SUCCESSFULLY = "exporting_successfully"
    FINISHED_SUCCESSFULLY = "finished_successfully"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


can_import_job_statuses = [
    JobStatus.PENDING,
    JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
]

can_export_job_statuses = [
    JobStatus.IMPORTING_SUCCESSFULLY,
    JobStatus.EXPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
]

retriable_job_statuses = [
    JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
    JobStatus.EXPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
]

terminated_job_statuses = [
    JobStatus.FINISHED_SUCCESSFULLY,
    JobStatus.CANCELLING,
    JobStatus.CANCELLED,
]


class Job(Base):
    __tablename__ = "job"

    id = Column(UUID(as_uuid=True), primary_key=True)

    import_service = Column(String, nullable=False)
    import_url = Column(String, nullable=False)
    import_token = Column(String)

    export_service = Column(String, nullable=False)
    export_url = Column(String, nullable=False)
    export_token = Column(String)

    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)

    path = Column(String)

    log = relationship("JobLog", cascade="all, delete")


class JobDuplicated(Exception):
    pass


class JobNotCancellable(Exception):
    pass


class JobNotRetriable(Exception):
    pass
