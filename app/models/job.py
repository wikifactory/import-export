import enum

from sqlalchemy import Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID

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
