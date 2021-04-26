import subprocess
from re import search
from typing import Dict

from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.exporters.base import BaseExporter
from app.models.job import Job, JobStatus
from app.service_validators.services import git_validator


def user_project_from_url(url: str) -> Dict:
    match = search(git_validator.keywords["regexes"][0], url)
    assert match
    return match.groupdict()


class GitExporter(BaseExporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id

    def process(self) -> None:

        job: Job = crud.job.get(self.db, self.job_id)
        assert job

        crud.job.update_status(self.db, db_obj=job, status=JobStatus.EXPORTING)

        try:
            self.push_to_repo_url()
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.EXPORTING_SUCCESSFULLY
            )
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.FINISHED_SUCCESSFULLY
            )
        except subprocess.CalledProcessError:
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE
            )

    def push_to_repo_url(self) -> None:

        job: Job = crud.job.get(self.db, self.job_id)

        assert job

        path_to_local_files = job.path

        # Init a git repo in the job's folder
        subprocess.check_output(["git", "init"], cwd=path_to_local_files)

        # Add all the files
        subprocess.check_output(["git", "add", "."], cwd=path_to_local_files)

        # Add the initial commit
        subprocess.check_output(
            [
                "git",
                "-c",
                f"user.name={settings.EXPORTER_GIT_USER}",
                "-c",
                f"user.email={settings.EXPORTER_GIT_MAIL}",
                "commit",
                f'--author="{settings.EXPORTER_GIT_USER} <{settings.EXPORTER_GIT_MAIL}>"',
                "-m",
                "Initial commit from imported project",
            ],
            cwd=path_to_local_files,
        )

        # Configure the remote to be the export_url
        subprocess.check_output(
            [
                "git",
                "remote",
                "add",
                "origin",
                self.get_auth_export_url_from_repo(job.export_url, job.export_token),
            ],
            cwd=path_to_local_files,
        )

        # Push
        subprocess.check_output(
            ["git", "branch", "-M", "main"],
            cwd=path_to_local_files,
        )

        subprocess.check_output(
            ["git", "push", "-u", "origin", "main"],
            cwd=path_to_local_files,
        )

    def get_auth_export_url_from_repo(self, repo_url: str, export_token: str) -> str:

        # TODO: identify service and dispatch the right url
        user_and_project = user_project_from_url(repo_url)
        return f"https://{user_and_project['user']}:{export_token}@github.com/{user_and_project['user']}/{user_and_project['project']}.git"
