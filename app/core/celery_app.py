from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "import_export_tasks",
    broker=settings.BROKER_URL,
    task_always_eager=not bool(settings.BROKER_URL),
)
