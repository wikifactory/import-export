from fastapi import APIRouter, HTTPException
from ..controller.importer_proxy import ImporterProxy

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
        print("OK")
        processing_prx = ImporterProxy()
        result = await processing_prx.handle_request(body)
        return result
