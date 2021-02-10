from fastapi import APIRouter
from fastapi.responses import JSONResponse
from enum import Enum

# from app.models import add_job_to_db, connect_to_db
import app.models

from app.celery_tasks import (
    handle_post_manifest,
    handle_post_export,
    handle_get_job,
    generate_job_id,
    handle_get_unfinished_jobs,
)


router = APIRouter()
OUTPUT_FOLDER = "/tmp/outputs/"


@router.get("/manifests")
async def get_manifests():
    return {"manifests": []}


class OperationType(Enum):
    MANIFEST = "manifest"
    IMPORT_EXPORT = "import_export"


class JobParameters(Enum):
    IMPORT_URL = "import_url"
    IMPORT_TOKEN = "import_token"
    IMPORT_SERVICE = "import_service"
    EXPORT_URL = "export_url"
    EXPORT_TOKEN = "export_token"
    EXPORT_SERVICE = "export_service"
    TYPE = "type"


@router.post("/job")
def post_job(body: dict):

    if (
        JobParameters.IMPORT_URL.value not in body
        or JobParameters.IMPORT_SERVICE.value not in body
        or JobParameters.EXPORT_URL.value not in body
        or JobParameters.EXPORT_SERVICE.value not in body
    ):
        return JSONResponse(
            status_code=400,
            content={"error": "Job parameters not valid"},
        )
    else:

        selected_operation = ""

        # Check if the request includes the operation type
        if JobParameters.TYPE.value in body:

            # Is it a valid one?
            if (
                any(
                    x.value == body[JobParameters.TYPE.value]
                    for x in OperationType
                )
                is True
            ):
                # Valid operation, then select it
                selected_operation = body[JobParameters.TYPE.value]
            else:
                # Invalid operation, cancel request?
                return JSONResponse(
                    status_code=404,
                    content={"error": "Unknown operation type"},
                )

        else:  # By default, we will try the whole import-export process
            selected_operation = OperationType.IMPORT_EXPORT.value

        # If we need to generate the manifest...

        if selected_operation == OperationType.MANIFEST.value:
            # Generate the job_id
            job_id = generate_job_id()

            # Create the job
            app.models.add_job_to_db(body, job_id)

            # For the moment, we wait until the manifest has been generated
            manifest = handle_post_manifest.delay(body, job_id).get()

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
                body[JobParameters.IMPORT_URL.value],
                body[JobParameters.EXPORT_URL.value],
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
            app.models.add_job_to_db(body, job_id)

            # Start the celery task
            handle_post_export.delay(body, job_id)

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
def get_jobs(job_id):
    return JSONResponse(status_code=200, content=app.models.get_jobs())


@router.get("/unfinished_jobs")
def get_unfinished_jobs():
    return handle_get_unfinished_jobs()
