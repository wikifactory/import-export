from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.models import Job, JobStatus
from app.models import Session as DBSession
from app.models import StatusEnum

from app.celery_tasks import (
    handle_post_manifest,
    handle_post_export,
    handle_get_job,
    generate_job_id,
)

router = APIRouter()

OUTPUT_FOLDER = "/tmp/outputs/"


def add_job_to_db(options, job_id):

    session = DBSession()
    new_job = Job()
    new_job.job_id = job_id
    new_job.import_service = options["import_service"]
    new_job.import_token = options["import_token"]
    new_job.import_url = options["import_url"]

    new_job.export_service = options["export_service"]
    new_job.export_token = options["export_token"]
    new_job.export_url = options["export_url"]

    new_status = JobStatus()
    new_status.job_id = new_job.job_id
    new_status.job_status = StatusEnum.pending.value

    session.add(new_job)
    session.add(new_status)
    session.commit()


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

    add_job_to_db(body, job_id)

    handle_post_manifest.delay(body, job_id)
    return JSONResponse(
        status_code=200,
        content={"message": "Manifest generation process started", "job_id": job_id},
    )


@router.post("/export")
def export(body: dict):
    job_id = generate_job_id()

    add_job_to_db(body, job_id)

    handle_post_export.delay(body, job_id)
    return JSONResponse(
        status_code=200, content={"message": "Export process started", "job_id": job_id}
    )


@router.get("/job/{job_id}")
def get_job(job_id):
    return handle_get_job(job_id)
