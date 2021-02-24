import sentry_sdk
from celery.utils.log import get_task_logger

from app import crud
from app.api.deps import get_db
from app.core.celery_app import celery_app
from app.core.config import settings
from app.exporters import service_map as exporters_map
from app.importers import service_map as importers_map

logger = get_task_logger(__name__)
client_sentry = sentry_sdk.init(settings.SENTRY_DSN)


@celery_app.task
def process_job(job_id: str) -> None:
    db = get_db()
    job = crud.job.get(db, job_id)
    assert job

    if not crud.job.is_active(job):
        return

    if crud.job.can_import(job):
        Importer = importers_map[job.import_service]
        assert Importer
        importer = Importer(db, job.id)
        importer.process()

    if crud.job.can_export(job):
        Exporter = exporters_map[job.export_service]
        assert Exporter
        exporter = Exporter(db, job.id)
        exporter.process()
