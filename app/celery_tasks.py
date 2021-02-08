from app.celery_config import celery_app
from celery.utils.log import get_task_logger
from fastapi import HTTPException

import uuid

from app.models import get_job, get_unfinished_jobs, cancel_job
from app.job_methods import export_job, retry_job, generate_manifest


logger = get_task_logger(__name__)


def generate_job_id():
    return str(uuid.uuid4())


@celery_app.task
def handle_post_manifest(body: dict, job_id):

    if (
        "import_url" not in body
        or "import_service" not in body
        or "import_token" not in body
    ):
        raise HTTPException(status_code=500, detail="Missing fields")

    else:
        return generate_manifest(body, job_id)


@celery_app.task
def handle_post_export(body: dict, job_id):

    if (
        "import_url" not in body
        or "import_service" not in body
        or "import_token" not in body
        or "export_url" not in body
        or "export_service" not in body
        or "export_token" not in body
    ):
        raise HTTPException(status_code=500, detail="Missing fields")
        return ""

    else:
        return export_job(body, job_id)


@celery_app.task
def handle_post_retry(body: dict, job_id):

    if (
        "import_url" not in body
        or "import_service" not in body
        or "import_token" not in body
        or "export_url" not in body
        or "export_service" not in body
        or "export_token" not in body
    ):
        raise HTTPException(status_code=500, detail="Missing fields")
        return ""
    else:
        return retry_job(body, job_id)


def handle_get_job(job_id):
    job = get_job(job_id)

    if job is None:
        return {"error": "Job not found in the DB"}
    else:
        return {"job": job}


def handle_get_unfinished_jobs():
    return get_unfinished_jobs()


def handle_post_cancel(job_id):
    return cancel_job(job_id)
