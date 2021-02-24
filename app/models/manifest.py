from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from app.db.base_class import Base
from app.models.job import Job


class Manifest(Base):
    __tablename__ = "manifest"

    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job.id"), unique=True)
    job = relationship(
        Job, backref=backref("manifest", uselist=False, cascade="all, delete-orphan")
    )

    project_name = Column(String, nullable=False, server_default="")
    project_description = Column(String, nullable=False, server_default="")
    source_url = Column(String, nullable=False)
