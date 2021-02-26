from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.job import Job, JobStatus


class JobLog(Base):
    __tablename__ = "job_log"

    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job.id", ondelete="CASCADE"))
    job = relationship(
        Job,
        backref=backref("log", uselist=False, cascade="all, delete"),
    )
    timestamp = Column(DateTime, server_default=func.now())
    from_status = Column(Enum(JobStatus))
    to_status = Column(Enum(JobStatus), nullable=False)
