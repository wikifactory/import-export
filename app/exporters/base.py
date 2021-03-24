import shutil
import traceback
from types import FunctionType
from typing import Any, Iterable

from sqlalchemy.orm import Session


class BaseExporter:
    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def clean_download_folder(self, path: str) -> None:
        def onerror(function: FunctionType, path: str, excinfo: Iterable[Any]) -> None:
            print(f"While processing {path}")
            traceback.print_exception(*excinfo)

        shutil.rmtree(path, onerror=onerror)


class AuthRequired(Exception):
    pass


class NotReachable(Exception):
    pass
