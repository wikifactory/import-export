import os
from celery import Celery

celery_app = Celery(
    "import_export_tasks",
    broker=os.environ["BROKER_URL"],
    backend=os.environ["BACKEND_URL"],
)
