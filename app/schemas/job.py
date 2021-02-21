from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Job(BaseModel):
    id: str
    status: str


class OperationType(Enum):
    MANIFEST = "manifest"
    IMPORT_EXPORT = "import_export"


class JobCreate(BaseModel):
    import_url: str
    export_url: str
    import_service: str
    export_service: str
    import_token: Optional[str]
    export_token: Optional[str]
    type: Optional[OperationType]
