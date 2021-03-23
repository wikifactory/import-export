from sqlalchemy.orm import Session

from app.schemas.manifest import ManifestInput
from app.service_validators.base_validator import ServiceValidator


class BaseImporter:

    validator: ServiceValidator = None

    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def populate_project_description(self, manifest_input: ManifestInput) -> None:
        raise NotImplementedError()
