import os
import re
import shutil
import subprocess

from sqlalchemy.orm import Session

from app import crud
from app.importers.base import BaseImporter
from app.models.job import Job, JobStatus
from app.schemas import ManifestInput


def clone_repository(url: str, path: str) -> None:
    subprocess.run(["git", "clone", "--depth", "1", url, path], check=True)


class GitImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):
        self.job_id = job_id
        self.db = db

    def process(self) -> None:

        self.on_import_started()

        job = crud.job.get(self.db, self.job_id)
        assert job

        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)
        url = job.import_url

        try:
            # First, we clone the repo into the tmp folder
            clone_repository(url, job.path)
        except subprocess.CalledProcessError:
            # TODO support "auth required" status when support for private repos is added
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE
            )
            return

        manifest_input = ManifestInput(job_id=job.id, source_url=url)

        # Fill some basic information of the project
        manifest_input.project_name = os.path.basename(os.path.normpath(url))

        # Remove the .git folder
        try:
            shutil.rmtree(os.path.join(job.path, ".git"))
        except Exception:
            print("Error deleting .git folder")

        # Load the project description
        self.populate_project_description(manifest_input)

        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
        )
        self.on_import_finished()

    def populate_project_description(self, manifest_input: ManifestInput) -> None:
        job: Job = crud.job.get(self.db, self.job_id)
        # use readme contents as project description
        with os.scandir(job.path) as directory_iterator:
            readme_candidates = [
                readme
                for readme in directory_iterator
                if readme.is_file()
                and re.search(r"README.md$", readme.name, re.IGNORECASE)
            ]

        if readme_candidates:
            chosen_readme = readme_candidates[0]
            # FIXME potentially dangerous!
            # we are opening and dumping the contents of a user-provided file
            with open(chosen_readme.path, "r") as file_handle:
                # FIXME maybe just read up to a certain length
                manifest_input.project_description = file_handle.read()

        # Set the number of total_items
        downloaded_files = sum([len(files) for _, _, files in os.walk(job.path)])

        crud.job.update_total_items(
            self.db, job_id=self.job_id, total_items=downloaded_files
        )

        # Since we cannot process the files one by one
        crud.job.update_imported_items(
            self.db, job_id=self.job_id, imported_items=downloaded_files
        )

        crud.manifest.update_or_create(self.db, obj_in=manifest_input)
