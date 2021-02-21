import os
import re

import pygit2

from app import crud
from app.importers.base import BaseImporter
from app.models.job import JobStatus
from app.models.manifest import Manifest


class IgnoreCredentialsCallbacks(pygit2.RemoteCallbacks):
    def credentials(self, url, username_from_url, allowed_types):
        return None

    def certificate_check(self, certificate, valid, host):
        return True


class GitImporter(BaseImporter):
    def __init__(self, db, job_id):
        self.job_id = job_id
        self.db = db

    def process(self):
        job = crud.job.get(self.db, self.job_id)
        crud.job.update_status(self.db, job, JobStatus.IMPORTING)
        url = job.import_url

        try:
            # First, we clone the repo into the tmp folder
            pygit2.clone_repository(
                url, job.path, callbacks=IgnoreCredentialsCallbacks()
            )
        except pygit2.errors.GitError:
            # TODO support "auth required" status when support for private repos is added
            crud.job.update_status(
                self.db, job, JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE
            )
            return

        # Create the manifest instance
        manifest = Manifest(path=job.path)

        # Fill some basic information of the project
        manifest.project_name = os.path.basename(os.path.normpath(url))
        manifest.source_url = url

        # use readme contents as project description
        readme_candidates = [
            readme
            for readme in os.listdir(manifest.path)
            if re.search(r"README.md$", readme, re.IGNORECASE)
        ]

        if readme_candidates:
            chosen_readme = readme_candidates[0]
            # FIXME potentially dangerous!
            # we are opening and dumping the contents of a user-provided file
            with open(chosen_readme, "r") as file_handle:
                manifest.project_description = file_handle.read()

        crud.job.update_status(self.db, job, JobStatus.IMPORTING_SUCCESSFULLY)
