import os
from pathlib import Path
from re import search

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from sqlalchemy.orm import Session

from app import crud
from app.importers.base import BaseImporter
from app.models.job import JobStatus

googledrive_folder_regex = r"^(https:\/\/drive\.google\.com\/drive\/(u\/[0-9]+\/)?folders\/.*(\?usp=sharing)?$)"


def is_folder(item):
    item.get("mimeType") == "application/vnd.google-apps.folder"


class GoogleDriveImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        self.drive = None
        self.tree_root = {"item": None, "children": {}}

    def validate_url(url):
        return bool(search(googledrive_folder_regex, url))

    def build_tree_recursively(self, folder_id, current_level):
        item_list = self.drive.ListFile(
            {"q": f"'{folder_id}' in parents and trashed=false"}
        ).GetList()

        for item in item_list:
            name = item.get("name")
            current_level.set(name, {"item": item, "children": {}})

        for (_, node) in current_level:
            item = node.get("item")
            if is_folder(item):
                self.process_folder_recursively(item.get("id"), node.get("children"))

    def download_tree_recursively(self, current_level, accumulated_path):
        Path(accumulated_path).mkdir(parents=True, exist_ok=True)

        for (name, node) in current_level:
            item = node.get("item")
            item_full_path = os.path.join(accumulated_path, name)
            if is_folder(item):
                self.download_tree_recursively(node.get("children"), item_full_path)
            else:
                item.GetContentFile(item_full_path)

    def process(self):
        job = crud.job.get(self.db)
        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)

        # FIXME - proper auth
        gauth = GoogleAuth()
        self.drive = GoogleDrive(gauth)

        self.build_tree_recursively(self.tree_root, job.import_url)
        # FIXME - this can probably be improved by flattening the tree first
        # and then starting downloads in parallel
        self.download_tree_recursively(self.tree_root, job.path)

        # TODO - populate manifest

        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
        )
