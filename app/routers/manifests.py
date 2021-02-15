from fastapi import APIRouter
from fastapi.responses import JSONResponse

# from app.models import add_job_to_db, connect_to_db
import app.models

from app.routers.manifests_types import (
    JobResponse,
    ErrorResponse,
    JobRequest,
    OperationType,
    Job,
    JobsResponse,
    UnfinishedJobsResponse,
)


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


@router.get(
    "/job/{job_id}",
    response_model=Job,
    responses={404: {"model": ErrorResponse}},
)
def get_job(job_id):
    result = handle_get_job(job_id)

    if "error" in result:
        return JSONResponse(
            status_code=404,
            content={
                "error": result["error"],
            },
        )
    else:
        return result


@router.get("/jobs", response_model=JobsResponse)
def get_jobs():
    jobs = app.models.get_jobs()
    return JSONResponse(status_code=200, content={"jobs": jobs})


@router.get("/unfinished_jobs", response_model=UnfinishedJobsResponse)
def get_unfinished_jobs():

    unfinished_jobs = handle_get_unfinished_jobs()

    print(unfinished_jobs)
    return unfinished_jobs
