import os
import pathlib
import shutil
import traceback
import zipfile
from io import BytesIO
from re import search
from typing import Dict

import requests
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.exporters.wikifactory import NoResult, UserErrors, wikifactory_api_request
from app.importers.base import BaseImporter, NotReachable
from app.importers.wikifactory_gql import repository_zip_query
from app.models.job import Job, JobStatus
from app.schemas.manifest import ManifestInput
from app.service_validators.services import wikifactory_validator


def space_slug_from_url(url: str) -> Dict:
    match = search(wikifactory_validator.keywords["regexes"][0], url)
    assert match
    return match.groupdict()


class WikifactoryImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):

        self.db = db
        self.job_id = job_id

    def process(self) -> None:

        job: Job = crud.job.get(self.db, self.job_id)
        assert job

        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)

        self.project_details = self.get_project_details()
        assert self.project_details

        try:
            self.download_files_from_zip_url(self.project_details["zip_url"])

            manifest_input = ManifestInput(job_id=job.id, source_url=job.import_url)
            manifest_input.project_name = os.path.basename(
                os.path.normpath(job.import_url)
            )

            self.populate_project_description(manifest_input)

            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
            )

        except (UserErrors):
            traceback.print_exc()

            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE
            )

    def get_project_details(self) -> Dict:
        job = crud.job.get(self.db, self.job_id)
        assert job

        variables = space_slug_from_url(job.import_url)

        try:
            project = wikifactory_api_request(
                repository_zip_query, job.import_token, variables, "project.result"
            )
        except (NoResult, UserErrors):
            raise NotReachable("Project not found in Wikifactory")

        return {
            "project_id": project["id"],
            "slug": project["slug"],
            "zip_url": f"{settings.WIKIFACTORY_API_BASE_URL}{ project['contributionUpstream']['zipArchiveUrl']}",
        }

    def download_files_from_zip_url(self, zip_url: str) -> None:
        job = crud.job.get(self.db, self.job_id)

        assert job

        response = requests.get(zip_url, verify=False)

        assert response.status_code == 200

        filebytes = BytesIO(response.content)
        zip_content = zipfile.ZipFile(filebytes)

        # Define the temporal destination of the uncompressed folder
        # This path will contain the real project folder
        tmp_job_name = "tmp_" + os.path.basename(job.path)
        tmp_job_path = os.path.join(os.path.dirname(job.path), tmp_job_name)

        # Create the target folder
        pathlib.Path(tmp_job_path).mkdir(parents=True, exist_ok=True)

        try:
            zip_content.extractall(tmp_job_path)

            # Make sure that the tmp folder only contains the real project folder
            elements_in_temp_folder = os.listdir(tmp_job_path)
            assert len(elements_in_temp_folder) == 1

            # Move the real project folder to the real job folder
            folder_path = os.path.join(tmp_job_path, elements_in_temp_folder[0])
            shutil.move(folder_path, job.path)

            # Delete the temporal folder, because it is not required anymore
            shutil.rmtree(tmp_job_path)
        except zipfile.error:
            traceback.print_exc()

    def populate_project_description(self, manifest_input: ManifestInput) -> None:
        job: Job = crud.job.get(self.db, self.job_id)

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
