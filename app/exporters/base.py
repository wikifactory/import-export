import shutil

from sqlalchemy.orm import Session


class BaseExporter:
    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def clean_download_folder(self, path: str) -> None:
        shutil.rmtree(path, ignore_errors=True)


class AuthRequired(Exception):
    pass


class NotReachable(Exception):
    pass
