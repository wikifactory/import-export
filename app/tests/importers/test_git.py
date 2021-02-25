import os
from typing import Any, Dict, Generator, List

import pygit2
import pytest
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.importers.git import GitImporter
from app.models.job import JobStatus
from app.models.job_log import JobLog
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.fixture(scope="function")
def basic_job(db: Session) -> Generator[Dict, None, None]:
    random_project_name = utils.random_lower_string()
    job_input = JobCreate(
        import_service="git",
        import_url=f"https://github.com/wikifactory/{random_project_name}",
        export_service="wikifactory",
        export_url=f"https://wikifactory.com/@user/{random_project_name}",
    )
    db_job = crud.job.create(db, obj_in=job_input)
    db_job.path = os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project")
    yield {
        "job_input": job_input,
        "db_job": db_job,
        "project_name": random_project_name,
    }
    crud.job.remove(db, id=db_job.id)


@pytest.fixture()
def clone_error(monkeypatch: Any) -> None:
    def mock_clone_repository_error(*args: List, **kwargs: Dict) -> None:
        raise pygit2.errors.GitError

    monkeypatch.setattr(pygit2, "clone_repository", mock_clone_repository_error)


@pytest.fixture()
def clone_repository(monkeypatch: Any) -> None:
    def mock_clone_repository(*args: List, **kwargs: Dict) -> pygit2.Repository:
        return pygit2.Repository()

    monkeypatch.setattr(pygit2, "clone_repository", mock_clone_repository)


@pytest.mark.usefixtures("clone_repository")
def test_git_importer(db: Session, basic_job: dict) -> None:
    job = basic_job["db_job"]
    importer = GitImporter(db, job.id)
    importer.process()
    importing_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.IMPORTING).one()
    )
    assert importing_status_log
    assert job.status is JobStatus.IMPORTING_SUCCESSFULLY
    assert job.manifest
    assert job.manifest.project_name == basic_job["project_name"]
    assert (
        job.manifest.project_description
        == """# sample-project

This is sample-project's README file\n"""
    )
    assert job.manifest.source_url == job.import_url


@pytest.mark.usefixtures("clone_error")
def test_git_importer_error(db: Session, basic_job: dict) -> None:
    job = basic_job["db_job"]
    importer = GitImporter(db, job.id)
    importer.process()
    assert job.status is JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE
