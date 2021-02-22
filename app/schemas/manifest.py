import uuid
from typing import Optional

from pydantic.main import BaseModel


class BaseManifest(BaseModel):
    project_name: Optional[str]
    project_description: Optional[str]
    source_url: str


class Manifest(BaseManifest):
    class Config:
        orm_mode = True


class ManifestInput(BaseManifest):
    job_id: uuid.UUID
