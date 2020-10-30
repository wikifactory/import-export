from fastapi import APIRouter, HTTPException
from ..controller.importer_proxy import ImporterProxy
from fastapi.responses import JSONResponse
import time

router = APIRouter()

# Define a route for retrieving a list of manifests
# TODO: filtering?


@router.get("/manifests")
async def get_manifests():
    return {"manifests": []}


# The route used to init the import/export process
'''
The body must contain the following parameters:
    - source_url
    - service
    - auth_token
'''


@router.post("/manifest")
async def post_manifest(body: dict):

    if("source_url" not in body or
       "service" not in body or
       "auth_token" not in body):
        raise HTTPException(status_code=500, detail="Missing fields")

    else:
        processing_prx = ImporterProxy()
        result_json_string = await processing_prx.handle_request(body)
        print("DONE!")


        outputfile_path = "/tmp/outputs/" + str(int(round(time.time() * 1000))) + ".json"

        text_file = open(outputfile_path, "w+")
        text_file.write(result_json_string)
        text_file.close()


        return result_json_string
        
