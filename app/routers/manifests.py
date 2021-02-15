from fastapi import APIRouter
from fastapi.responses import JSONResponse
from enum import Enum

# from app.models import add_job_to_db, connect_to_db
import app.models

from app.model.manifest import Manifest

from app.celery_tasks import (
    handle_post_manifest,
    handle_post_export,
    handle_get_job,
    generate_job_id,
    handle_get_unfinished_jobs,
)

from pydantic import BaseModel
from typing import Optional

router = APIRouter()
OUTPUT_FOLDER = "/tmp/outputs/"


class OperationType(Enum):
    MANIFEST = "manifest"
    IMPORT_EXPORT = "import_export"


class JobRequest(BaseModel):
    import_url: str
    export_url: str
    import_service: str
    export_service: str
    import_token: Optional[str] = ""
    export_token: Optional[str] = ""
    type: Optional[OperationType] = OperationType.IMPORT_EXPORT.value

    def toJson(self):

        return {
            "import_url": self.import_url,
            "export_url": self.export_url,
            "import_service": self.import_service,
            "export_service": self.export_service,
            "import_token": self.import_token,
            "export_token": self.export_token,
        }


@router.get("/manifests")
async def get_manifests():
    return {"manifests": []}


class JobResponse(BaseModel):
    message: str
    job_id: str
    manifest: Optional[Manifest]


class ErrorResponse(BaseModel):
    error: str


@router.post(
    "/job",
    response_model=JobResponse,
    responses={422: {"model": ErrorResponse}},
)
def post_job(body: JobRequest):

    selected_operation = None

    if hasattr(body, "type"):
        selected_operation = body.type.value
    else:
        selected_operation = OperationType.IMPORT_EXPORT.value

    # If we need to generate the manifest...

    if selected_operation == OperationType.MANIFEST.value:
        # Generate the job_id
        job_id = generate_job_id()

        # Create the job
        app.models.add_job_to_db(body.toJson(), job_id)

        # For the moment, we wait until the manifest has been generated
        manifest = handle_post_manifest.delay(body.toJson(), job_id).get()

        return JSONResponse(
            status_code=200,
            content={
                "message": "Manifest generation process started",
                "job_id": job_id,
                "manifest": manifest,
            },
        )

    # Else if we need to process the import-export flow....
    elif selected_operation == OperationType.IMPORT_EXPORT.value:

        # First check if an active job exists for that url combination
        # For the moment, we say that an active job is one that does not
        # have the "cancelled" or "exported_succesfully" statuses
        # (this definition may be different in the future)
        already_present = app.models.import_export_job_combination_exists(
            body.import_service,
            body.export_service,
        )

        if already_present is True:  # A combination already exists
            return JSONResponse(
                status_code=422,
                content={
                    "error": "An active job for that (import_url, export_url) already exists",
                },
            )

        # Otherwise, we can perform the import export job

        # Generate the job_id
        job_id = generate_job_id()

        # Create the job
        app.models.add_job_to_db(body.toJson(), job_id)

        # Start the celery task
        handle_post_export.delay(body.toJson(), job_id)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Export process started",
                "job_id": job_id,
            },
        )


@router.get("/job/{job_id}")
def get_job(job_id):
    return handle_get_job(job_id)


@router.get("/jobs")
def get_jobs():
    return JSONResponse(status_code=200, content=app.models.get_jobs())


@router.get("/unfinished_jobs")
def get_unfinished_jobs():
    return handle_get_unfinished_jobs()
