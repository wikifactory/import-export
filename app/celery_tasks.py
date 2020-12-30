from app.celery_config import celery_app
from celery.utils.log import get_task_logger
from fastapi import HTTPException
from app.controller.importer_proxy import ImporterProxy
from app.controller.exporter_proxy import ExporterProxy


import time

logger = get_task_logger(__name__)


def generate_request_id():
    return str(int(round(time.time() * 1000)))


@celery_app.task
def handle_post_manifest(body: dict):

    logger.info("BEFORE")
    if (
        "import_url" not in body
        or "import_service" not in body
        or "import_token" not in body
    ):
        raise HTTPException(status_code=500, detail="Missing fields")

    else:
        request_id = generate_request_id()

        logger.info(body)

        processing_prx = ImporterProxy(request_id)
        manifest = processing_prx.handle_request(body)
        return manifest

    logger.info("after")


@celery_app.task
def handle_post_export(body: dict):

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
        request_id = generate_request_id()

        # body contains the parameters for this request (tokens and so on)

        logger.info("Starting the import process...")
        processing_prx = ImporterProxy(request_id)
        manifest = processing_prx.handle_request(body)
        logger.info("Importing process finished!")
        logger.info(manifest)
        logger.info("Starting the export Process...")
        export_proxy = ExporterProxy(request_id)

        result = export_proxy.export_manifest(manifest, body)

        logger.info("Process done!")

        return result
