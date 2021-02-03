from fastapi import APIRouter
from fastapi.responses import JSONResponse

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


# The route used to init the import/export process
"""
The body must contain the following parameters:
    - import_url
    - import_service
    - import_token
    - export_url
    - export_service
    - export_token
"""


@router.post("/manifest")
def post_manifest(body: dict):
    job_id = generate_job_id()

    app.models.add_job_to_db(body, job_id)

    manifest = handle_post_manifest.delay(body, job_id).get()
    return JSONResponse(
        status_code=200,
        content={
            "message": "Manifest generation process started",
            "job_id": job_id,
            "manifest": manifest,
        },
    )


@router.post("/export")
def export(body: dict):
    job_id = generate_job_id()

    print(job_id)

    app.models.add_job_to_db(body, job_id)

    handle_post_export.delay(body, job_id)
    return JSONResponse(
        status_code=200,
        content={"message": "Export process started", "job_id": job_id},
    )


@router.get("/job/{job_id}")
def get_job(job_id):
    return handle_get_job(job_id)


@router.get("/unfinished_jobs")
def get_unfinished_jobs():
    return handle_get_unfinished_jobs()
