from fastapi import FastAPI
from .routers import manifests
# from model.manifest import Manifest
# import json

app = FastAPI()
app.include_router(manifests.router)
