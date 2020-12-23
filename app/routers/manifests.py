from fastapi import APIRouter, HTTPException
from app.controller.importer_proxy import ImporterProxy
from app.controller.exporter_proxy import ExporterProxy

import time

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
    - source_url
    - service
    - auth_token
"""


def generate_request_id():
    return str(int(round(time.time() * 1000)))


@router.post("/manifest")
async def post_manifest(body: dict):

    if "source_url" not in body or "service" not in body or "auth_token" not in body:
        raise HTTPException(status_code=500, detail="Missing fields")

    else:
        request_id = generate_request_id()

        processing_prx = ImporterProxy(request_id)
        result_json_string = await processing_prx.handle_request(body)

        print("DONE!")

        outputfile_path = OUTPUT_FOLDER + request_id + ".json"

        text_file = open(outputfile_path, "w+")
        text_file.write(result_json_string)
        text_file.close()

        return result_json_string


@router.post("/export")
async def export(body: dict):

    print(body)

    if (
        "import_url" not in body
        or "import_service" not in body
        or "import_token" not in body
        or "export_url" not in body
        or "export_service" not in body
        or "export_token" not in body
    ):
        raise HTTPException(status_code=500, detail="Missing fields")

    else:
        request_id = generate_request_id()

        # body contains the parameters for this request (tokens and so on)

        print("Starting the import process...")
        processing_prx = ImporterProxy(request_id)
        manifest = await processing_prx.handle_request(body)
        print("Importing process finished!")

        print("Starting the export Process...")
        export_proxy = ExporterProxy(request_id)

        result = await export_proxy.export_manifest(manifest, body)

        print("Process done!")

        return result

