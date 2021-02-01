from celery import Celery


BROKER_URL = "redis://redis:6379/0"
BACKEND_URL = "redis://redis:6379/0"


celery_app = Celery("import_export_tasks", backend=BACKEND_URL, broker=BROKER_URL)
