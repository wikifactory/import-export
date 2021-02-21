import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base
from app.models.job import JobStatus


class JobLog(Base):
    __tablename__ = "job_log"

    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    from_status = Column(Enum(JobStatus), nullable=False)
    to_status = Column(Enum(JobStatus), nullable=False)
