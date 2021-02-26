import uuid
from typing import Optional

from pydantic import BaseModel, HttpUrl

from app.models.job import JobStatus


class BaseJob(BaseModel):
    import_url: HttpUrl
    export_url: HttpUrl
    import_service: str
    export_service: str
    import_token: Optional[str] = None
    export_token: Optional[str] = None


class Job(BaseJob):
    id: uuid.UUID
    status: JobStatus
    general_progress: float
    status_progress: float

    class Config:
        orm_mode = True


class JobCreate(BaseJob):
    pass
