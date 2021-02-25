import enum
import uuid

from sqlalchemy import Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql.sqltypes import Integer

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

importing_statuses = [
    JobStatus.IMPORTING,
    JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
    JobStatus.IMPORTING_SUCCESSFULLY,
]


exporting_statuses = [
    JobStatus.EXPORTING,
    JobStatus.EXPORTING_ERROR_AUTHORIZATION_REQUIRED,
    JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
    JobStatus.EXPORTING_SUCCESSFULLY,
]


class Job(Base):
    __tablename__ = "job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    import_service = Column(String, nullable=False)
    import_url = Column(String, nullable=False)
    import_token = Column(String)

    export_service = Column(String, nullable=False)
    export_url = Column(String, nullable=False)
    export_token = Column(String)

    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)

    total_items = Column(Integer, nullable=False, server_default="0")
    imported_items = Column(Integer, nullable=False, server_default="0")
    exported_items = Column(Integer, nullable=False, server_default="0")

    path = Column(String)

    @hybrid_property
    def general_progress(self) -> float:
        # FIXME

        if self.status is JobStatus.PENDING:
            return 0
        elif self.status in terminated_job_statuses:
            return 1

        if self.status in importing_statuses:
            return 0.25
        elif self.status in exporting_statuses:
            return 0.75

        return 0.5

    @hybrid_property
    def status_progress(self) -> float:
        if self.total_items:
            if self.status in importing_statuses:
                return self.imported_items / self.total_items
            elif self.status in exporting_statuses:
                return self.exported_items / self.total_items

        return 0


class JobDuplicated(Exception):
    pass


class JobNotCancellable(Exception):
    pass


class JobNotRetriable(Exception):
    pass
