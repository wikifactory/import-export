from sqlalchemy.orm import Session


class BaseImporter:
    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()
