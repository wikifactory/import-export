import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.api_v1.api import api_router
from app.core.config import settings

# TODO - include OpenAPI
app = FastAPI(title=settings.PROJECT_NAME)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

try:
    if not os.path.exists(settings.DOWNLOAD_BASE_PATH):
        print("Creating tmp folder")
        os.makedirs(settings.DOWNLOAD_BASE_PATH)

except Exception as e:
    print(e)

app.include_router(api_router, prefix=settings.API_V1_STR)
