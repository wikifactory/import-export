import enum
from typing import Callable, Dict, List

from mypy.types import Any
from sqlalchemy.orm import Session

from app.schemas.manifest import ManifestInput


class HooksEnum(enum.Enum):
    ON_IMPORT_STARTED = "onImportStarted"
    ON_FILE_DOWNLOADED = "onFileDownloaded"
    ON_IMPORT_FINISHED = "onImportFinished"


class BaseImporter:

    hooks: Dict[str, List[Callable]] = {}

    def __init__(self, db: Session, job_id: str):
        raise NotImplementedError()

    def process(self) -> None:
        raise NotImplementedError()

    def populate_project_description(self, manifest_input: ManifestInput) -> None:
        raise NotImplementedError()

    def on_import_started(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(HooksEnum.ON_IMPORT_STARTED.value, *args, **kwargs)

    def on_import_finished(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(
            HooksEnum.ON_IMPORT_FINISHED.value, *args, **kwargs
        )

    def on_file_downloaded(self, *args: Any, **kwargs: Any) -> None:
        self.launch_hooks_for_status(
            HooksEnum.ON_FILE_DOWNLOADED.value, *args, **kwargs
        )

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
