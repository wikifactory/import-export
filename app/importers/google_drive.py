import os
from pathlib import Path
from re import search

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import ApiRequestError, FileNotDownloadableError
from sqlalchemy.orm import Session

from app import crud
from app.importers.base import BaseImporter
from app.models.job import JobStatus
from app.schemas import ManifestInput

googledrive_folder_regex = r"^https?:\/\/drive\.google\.com\/drive\/(u\/[0-9]+\/)?folders\/(?P<folder_id>[-\w]{25,})"

folder_mimetype = "application/vnd.google-apps.folder"


def is_folder(item):
    return item.get("mimeType") == folder_mimetype


def folder_id_from_url(url):
    match = search(googledrive_folder_regex, url)
    return match.group("folder_id")


class GoogleDriveImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        self.drive = None
        self.tree_root = {"item": None, "children": {}}

    def validate_url(self, url):
        return bool(search(googledrive_folder_regex, url))

    def build_tree_recursively(self, current_level, folder_id):
        item_list = self.drive.ListFile(
            {"q": f"'{folder_id}' in parents and trashed=false"}
        ).GetList()

        for item in item_list:
            name = item.get("title")
            current_level[name] = {"item": item, "children": {}}

        for node in current_level.values():
            item = node.get("item")
            if is_folder(item):
                self.build_tree_recursively(node.get("children"), item.get("id"))

    def download_tree_recursively(self, current_level, accumulated_path):
        Path(accumulated_path).mkdir(parents=True, exist_ok=True)

        for (name, node) in current_level.items():
            item = node.get("item")
            item_full_path = os.path.join(accumulated_path, name)
            if is_folder(item):
                self.download_tree_recursively(node.get("children"), item_full_path)
            else:
                item.GetContentFile(item_full_path)

    def process(self):
        job = crud.job.get(self.db, self.job_id)
        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)

        gauth = GoogleAuth()
        # FIXME - for security and trust purposes, it is probably better
        # to use the "drive.file" scope (because "drive.readonly" can read the full Drive contents).
        # As a downside, it needs the private folders to be shared with the app in advance.
        gauth.settings["oauth_scope"] = "https://www.googleapis.com/auth/drive.readonly"

        if job.import_token:
            gauth.Auth(job.import_token)

        self.drive = GoogleDrive(gauth)

        folder_id = folder_id_from_url(job.import_url)

        try:
            res = self.drive.ListFile(
                {"q": f"'{folder_id}' and trashed=false"}
            ).GetList()

            [root_folder] = res

            self.tree_root["item"] = root_folder

            self.build_tree_recursively(self.tree_root["children"], folder_id)
            # FIXME - this can probably be improved by flattening the tree first
            # and then starting downloads in parallel
            self.download_tree_recursively(self.tree_root["children"], job.path)
        except (ApiRequestError, FileNotDownloadableError):
            # FIXME - store/pass this API clients can use it
            # auth_url = gauth.GetAuthUrl()
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
            )
            return

        manifest_input = ManifestInput(job_id=job.id, source_url=job.import_url)
        manifest_input.project_name = self.tree_root.get("item").get("title")
        # TODO - add project_description to manifest

        crud.manifest.update_or_create(self.db, obj_in=manifest_input)
        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
        )
