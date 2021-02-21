import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class BaseJob(BaseModel):
    import_url: HttpUrl
    export_url: HttpUrl
    import_service: str
    export_service: str
    import_token: Optional[str] = None
    export_token: Optional[str] = None


class Job(BaseJob):
    id: uuid.UUID
    status: Enum

    class Config:
        orm_mode = True


class JobCreate(BaseJob):
    pass
