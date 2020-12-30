from fastapi import APIRouter
from app.celery_tasks import handle_post_manifest, handle_post_export

router = APIRouter()

OUTPUT_FOLDER = "/tmp/outputs/"


# Define a route for retrieving a list of manifests
# TODO: filtering?


@router.get("/manifests")
async def get_manifests():
    return {"manifests": []}


# The route used to init the import/export process
"""
The body must contain the following parameters:
    - import_url
    - import_service
    - import_token
    - export_url
    - export_service
    - export_token
"""


@router.post("/manifest")
def post_manifest(body: dict):
    return handle_post_manifest.delay(body).get()


@router.post("/export")
def export(body: dict):
    return handle_post_export.delay(body).get()

