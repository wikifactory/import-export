import uuid

from celery.utils.log import get_task_logger

from app.celery_config import celery_app
from app.controller.exporter_proxy import ExporterProxy
from app.controller.importer_proxy import ImporterProxy
from app.job_methods import retry_job
from app.models import cancel_job, get_job, get_unfinished_jobs

logger = get_task_logger(__name__)


def generate_job_id():
    return str(uuid.uuid4())


@celery_app.task
def handle_post_manifest(body: dict, job_id):

    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(body)
    return manifest.toJson()


@celery_app.task
def handle_post_export(body: dict, job_id):

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
