from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from app.model.manifest import Manifest


class OperationType(Enum):
    MANIFEST = "manifest"
    IMPORT_EXPORT = "import_export"


class JobRequest(BaseModel):
    import_url: str
    export_url: str
    import_service: str
    export_service: str
    import_token: Optional[str]
    export_token: Optional[str]
    type: Optional[OperationType]

    def toJson(self):

        return {
            "import_url": self.import_url,
            "export_url": self.export_url,
            "import_service": self.import_service,
            "export_service": self.export_service,
            "import_token": self.import_token,
            "export_token": self.export_token,
        }


class JobResponse(BaseModel):
    message: str
    job_id: str
    manifest: Optional[Manifest]


class ErrorResponse(BaseModel):
    error: str


class JobSimpleEntryEntry(BaseModel):
    id: str
    status: str


class JobsResponse(BaseModel):
    jobs: List[JobSimpleEntryEntry]


class UnfinishedJobsResponse(BaseModel):
    unfinished_jobs: List[str]


class Job(BaseModel):
    job_id: str
    job_status: str
    job_progress: float
    overall_process: float
