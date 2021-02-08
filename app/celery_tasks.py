from app.celery_config import celery_app
from celery.utils.log import get_task_logger
from fastapi import HTTPException
from app.controller.importer_proxy import ImporterProxy
from app.controller.exporter_proxy import ExporterProxy
import uuid

from app.models import get_job, get_unfinished_jobs, cancel_job, set_retry_job


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

        logger.info(body)

        processing_prx = ImporterProxy(job_id)
        manifest = processing_prx.handle_request(body)
        return manifest.toJson()


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


def export_job(body: dict, job_id):
    # body contains the parameters for this request (tokens and so on)

    logger.info("Starting the import process...")

    # Configure the importer
    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(body)

    if manifest is None:
        return {"error": "The manifest could not be generated"}

    logger.info("Importing process finished!")
    # logger.info(manifest)
    logger.info("Starting the export Process...")
    # Configure the exporter
    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, body)

    logger.info("Process done!")
    return result


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


def retry_job(body: dict, job_id):
    # We can now proceed to the whole process
    logger.info("Retrying job: {}".format(job_id))

    # Add the "retry" status to the db
    set_retry_job(job_id)

    # And now we can do the whole import-export process again
    processing_prx = ImporterProxy(job_id)

    manifest = processing_prx.handle_request(body)

    if manifest is None:
        return {
            "error": "The manifest for job {} could not be generated".format(
                job_id
            )
        }

    logger.info("Importing process finished!")

    logger.info("Starting the export Process...")
    # Configure the exporter
    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, body)

    logger.info("The retry process succeded!")
    return result


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
