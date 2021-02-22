from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base


class Manifest(Base):
    __tablename__ = "manifest"

    id = Column(Integer, primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job.id"), unique=True)

    project_name = Column(String, nullable=False, server_default="")
    project_description = Column(String, nullable=False, server_default="")
    source_url = Column(String, nullable=False)
