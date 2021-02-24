import os
import re
from re import search

import pygit2
from sqlalchemy.orm import Session

from app import crud
from app.importers.base import BaseImporter
from app.models.job import JobStatus
from app.schemas import ManifestInput

# FIXME - there's git beyond github and gitlab
popular_git_regex = r"^https?:\/\/(www\.)?git(hub|lab)\.com\/(?P<organization>[\w-]+)/(?P<project>[\w-]+)"


class IgnoreCredentialsCallbacks(pygit2.RemoteCallbacks):
    def credentials(self, url, username_from_url, allowed_types):
        return None

    def certificate_check(self, certificate, valid, host):
        return True


def validate_url(url):
    return bool(search(popular_git_regex, url))


class GitImporter(BaseImporter):
    def __init__(self, db: Session, job_id: str):
        self.job_id = job_id
        self.db = db

    def process(self):
        job = crud.job.get(self.db, self.job_id)
        crud.job.update_status(self.db, db_obj=job, status=JobStatus.IMPORTING)
        url = job.import_url

        try:
            # First, we clone the repo into the tmp folder
            pygit2.clone_repository(
                url, job.path, callbacks=IgnoreCredentialsCallbacks()
            )
        except pygit2.errors.GitError:
            # TODO support "auth required" status when support for private repos is added
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE
            )
            return

        manifest_input = ManifestInput(job_id=job.id, source_url=url)

        # Fill some basic information of the project
        manifest_input.project_name = os.path.basename(os.path.normpath(url))

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

        crud.manifest.update_or_create(self.db, obj_in=manifest_input)
        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.IMPORTING_SUCCESSFULLY
        )
