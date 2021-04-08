import os
from pathlib import Path
from re import search
from typing import Dict, List, Optional

import dropbox
from dropbox.dropbox_client import BadInputException, Dropbox
from dropbox.exceptions import ApiError, AuthError, BadInputError, HttpError
from dropbox.files import FolderMetadata
from sqlalchemy.orm import Session

from app import crud
from app.importers.base import BaseImporter
from app.models.job import Job, JobStatus
from app.schemas import ManifestInput
from app.service_validators.services import dropbox_validator

dropbox_shared_folder_regex = dropbox_validator.keywords["regexes"][0]
dropbox_user_folder_regex = dropbox_validator.keywords["regexes"][1]


def validate_url_shared_folder(url: str) -> bool:
    return bool(search(dropbox_shared_folder_regex, url))


def validate_url_user_folder(url: str) -> bool:
    return bool(search(dropbox_user_folder_regex, url))


def get_url_details(url: str) -> Dict[str, str]:

    url_details = {}

    if validate_url_shared_folder(url) is True:
        url_details["type"] = "shared"
        url_details["path"] = url

    elif validate_url_user_folder(url) is True:
        url_details["type"] = "user_folder"
        search_result = search(dropbox_user_folder_regex, url)
        assert search_result
        url_details["path"] = "/" + search_result.group("path")

    return url_details


class DropboxImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        self.dropbox_handler: Optional[Dropbox] = None
        self.tree_root: Dict = {
            "entry": FolderMetadata(id="root-folder", name="root-folder"),
            "children": {},
        }

    def process(self) -> None:

        job: Job = crud.job.get(self.db, self.job_id)
        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)

        try:
            if len(job.import_token) == 0:
                # Use a default, not valid token
                self.dropbox_handler = dropbox.Dropbox(
                    oauth2_access_token="R2D2c3p0p4dm34n4k1n3Ia"
                )
            else:
                self.dropbox_handler = dropbox.Dropbox(
                    oauth2_access_token=job.import_token
                )
        except (BadInputException, HttpError):
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
            )
            return

        url_details = get_url_details(job.import_url)

        assert url_details

        self.url_type = url_details["type"]

        try:
            self.build_tree_recursively(self.tree_root["children"], url_details["path"])
            self.download_tree_recursively(self.tree_root["children"], job.path)
        except (AuthError, HttpError, BadInputError):
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
            )
            return
        except (ApiError):
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
            )
            return

        manifest_input = ManifestInput(job_id=job.id, source_url=job.import_url)

        root_entry = self.tree_root.get("entry")
        assert root_entry

        self.root_entry = root_entry
        manifest_input.project_name = root_entry.name

        # Set the number of total_items
        crud.job.update_total_items(
            self.db, job_id=self.job_id, total_items=job.imported_items
        )

        crud.manifest.update_or_create(self.db, obj_in=manifest_input)

        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
        )

    def get_entries_from_folder(self, folder_path: str) -> List[dropbox.files.Metadata]:

        assert self.dropbox_handler

        entries = []

        if self.url_type == "shared":

            # Change the type to id to treat the following folders as ids
            self.url_type = "id"

            link = dropbox.files.SharedLink(
                url=folder_path,
            )

            # When handling a shared_link folder, treat the first iteration different
            result = self.dropbox_handler.files_list_folder(path="", shared_link=link)

        elif self.url_type == "user_folder" or self.url_type == "id":
            result = self.dropbox_handler.files_list_folder(folder_path)

        entries.extend(result.entries)

        while result.has_more:
            result = self.dropbox_handler.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        return entries

    def build_tree_recursively(self, current_level: Dict, folder_url: str) -> None:

        entries = self.get_entries_from_folder(folder_url)

        for entry in entries:
            name = entry.name
            current_level[name] = {"entry": entry, "children": {}}

        for node in current_level.values():
            entry = node.get("entry")
            if isinstance(entry, dropbox.files.FileMetadata):
                pass
            elif isinstance(entry, dropbox.files.FolderMetadata):
                self.build_tree_recursively(node.get("children"), entry.id)

    def download_tree_recursively(
        self, current_level: Dict, accumulated_path: str
    ) -> None:

        assert self.dropbox_handler

        Path(accumulated_path).mkdir(parents=True, exist_ok=True)

        for (name, node) in current_level.items():
            entry = node.get("entry")
            entry_full_path = os.path.join(accumulated_path, name)

            if isinstance(entry, dropbox.files.FolderMetadata):
                self.download_tree_recursively(node.get("children"), entry_full_path)
            else:
                self.dropbox_handler.files_download_to_file(
                    entry_full_path, entry.path_lower
                )
                print("Downloaded file: {}".format(entry.name))
                crud.job.increment_imported_items(self.db, job_id=self.job_id)
