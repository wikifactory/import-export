from sqlalchemy.orm import Session

from app.schemas.manifest import ManifestInput


class BaseImporter:
    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def populate_project_description(self, manifest_input: ManifestInput) -> None:
        raise NotImplementedError()
