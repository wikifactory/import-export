import enum
import shutil
import traceback
from types import FunctionType
from typing import Any, Callable, Dict, Iterable, List

from sqlalchemy.orm import Session


class HooksEnum(enum.Enum):
    ON_EXPORT_STARTED = ""
    ON_FILE_UPLOADED = ""
    ON_EXPORT_FINISHED = ""


class BaseExporter:

    hooks: Dict[str, List[Callable]] = {}

    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def clean_download_folder(self, path: str) -> None:
        def onerror(function: FunctionType, path: str, excinfo: Iterable[Any]) -> None:
            print(f"While processing {path}")
            traceback.print_exception(*excinfo)

        shutil.rmtree(path, onerror=onerror)

    def on_export_started(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(HooksEnum.ON_EXPORT_STARTED.value, *args, **kwargs)

    def on_export_finished(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(
            HooksEnum.ON_EXPORT_FINISHED.value, *args, **kwargs
        )

    def on_file_uploaded(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(HooksEnum.ON_FILE_UPLOADED.value, *args, **kwargs)

    def launch_hooks_for_status(self, status: str, *args: Any, **kwargs: Any) -> None:
        if status in self.hooks:
            for h in self.hooks[status]:
                h(*args, **kwargs)

    def add_hook_for_status(self, status: str, hook: Callable) -> None:

        if status not in self.hooks:
            self.hooks[status] = []

        if hook not in self.hooks[status]:
            self.hooks[status].append(hook)
        else:
            print("Triying to set the same hook for the same status more than once")

    def remove_hook_from_status(self, status: str, hook: Callable) -> None:
        self.hooks.pop(status, None)


class AuthRequired(Exception):
    pass


class NotReachable(Exception):
    pass
