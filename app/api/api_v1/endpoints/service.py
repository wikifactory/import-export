from typing import Any

from fastapi import APIRouter

from app import schemas
from app.exporters import validator_map as export_validators
from app.importers import validator_map as import_validators

router = APIRouter()


@router.post("/validate", response_model=schemas.Service)
def validate_url(*, service_input: schemas.ServiceInput) -> Any:
    # FIXME - rethink URL validation, as currently:
    #   - it's tied to specific platforms for git
    #   - in the code, it's tied to an exporter or importer, while it should sit on top
    for (service_name, is_valid) in import_validators.items():
        if is_valid(service_input.url):
            return {"name": service_name}

    for (service_name, is_valid) in export_validators.items():
        if is_valid(service_input.url):
            return {"name": service_name}

    return {"name": "unknown"}
