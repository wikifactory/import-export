from app.celery_config import celery_app
from celery.utils.log import get_task_logger
from fastapi import HTTPException
from app.controller.importer_proxy import ImporterProxy
from app.controller.exporter_proxy import ExporterProxy
import uuid

from app.models import get_job


logger = get_task_logger(__name__)


def generate_job_id():
    return str(uuid.uuid1())
    # return str(int(round(time.time() * 1000)))


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
        return manifest


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

        # body contains the parameters for this request (tokens and so on)

        logger.info("Starting the import process...")

        # Configure the importer
        processing_prx = ImporterProxy(job_id)
        manifest = processing_prx.handle_request(body)
        logger.info("Importing process finished!")
        # logger.info(manifest)
        logger.info("Starting the export Process...")
        # Configure the exporter
        export_proxy = ExporterProxy(job_id)
        result = export_proxy.export_manifest(manifest, body)

        logger.info("Process done!")

        return result


def handle_get_job(job_id):
    job = get_job(job_id)

    if job is None:
        return {"error": "Job not found in the DB"}
    else:
        return {"job": job}
