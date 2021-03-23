from typing import Any

from fastapi import APIRouter

from app import schemas
from app.service_validators.services import available_services

router = APIRouter()


@router.post("/validate", response_model=schemas.Service)
def validate_url(*, service_input: schemas.ServiceInput) -> Any:

    for service in available_services:
        service_name = service.validate_url(service_input.url)

        if service_name is not None:
            return {"name": service_name}

    return {"name": "unknown"}
