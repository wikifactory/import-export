import sentry_sdk
from celery.utils.log import get_task_logger

from app.api.deps import get_db
from app.core.celery_app import celery_app
from app.core.config import settings
from app.exporters import service_map as exporters_map
from app.importers import service_map as importers_map
from app.models.job import Job, JobStatus

logger = get_task_logger(__name__)
client_sentry = sentry_sdk.init(settings.SENTRY_DSN)


@celery_app.task
def process_job(job: Job):
    db = get_db()

    if job.status in [
        JobStatus.PENDING,
        JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
        JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
        JobStatus.CANCELLED,
    ]:
        Importer = importers_map[job.import_service]
        importer = Importer(db, job.id)
        importer.import()
    elif job.status in [
        JobStatus.IMPORTING_SUCCESSFULLY,
        JobStatus.EXPORTING_ERROR_AUTHORIZATION_REQUIRED,
        JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
    ]:
        Exporter = exporters_map[job.export_service]
        exporter = Exporter(db, job.id)
        exporter.export()

    return
