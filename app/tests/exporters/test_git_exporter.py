import os
from typing import Any, Dict, Generator, List

import py
import pytest
from sqlalchemy.orm import Session

from app import crud
from app.exporters.git import (
    GitCommitError,
    GitExporter,
    GitPushError,
    GitRemoteOriginError,
)
from app.models.job import JobStatus
from app.models.job_log import Job, JobLog
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.fixture(scope="function")
def basic_job(db: Session, tmpdir: py.path.local) -> Generator[Dict, None, None]:
    random_project_name = utils.random_lower_string()
    job_input = JobCreate(
        import_service="git",
        import_url=f"https://github.com/wikifactory/{random_project_name}",
        export_service="git",
        export_url=f"https://github.com/user/{random_project_name}",
    )
    db_job = crud.job.create(db, obj_in=job_input)

    db_job.path = os.path.join(tmpdir, str(db_job.id))

    yield {
        "job_input": job_input,
        "db_job": db_job,
        "project_name": random_project_name,
    }

    crud.job.remove(db, id=db_job.id)


def mock_command_success(*args: List, **kwargs: Dict) -> None:
    # Simulates that the process returned 0
    pass


@pytest.fixture
def mock_git_success(monkeypatch: Any) -> None:
    monkeypatch.setattr(GitExporter, "git_command_init_repo", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_add_all_files", mock_command_success)
    monkeypatch.setattr(
        GitExporter, "git_command_add_initial_commit", mock_command_success
    )
    monkeypatch.setattr(
        GitExporter, "git_command_set_remote_origin", mock_command_success
    )
    monkeypatch.setattr(GitExporter, "git_command_set_branch", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_push_to_remote", mock_command_success)


@pytest.fixture
def mock_git_error_on_commit(monkeypatch: Any) -> None:
    def raise_commit_error(self: GitExporter, path_to_local_files: str) -> None:
        raise GitCommitError("")

    monkeypatch.setattr(GitExporter, "git_command_init_repo", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_add_all_files", mock_command_success)
    monkeypatch.setattr(
        GitExporter, "git_command_add_initial_commit", raise_commit_error
    )


@pytest.fixture
def mock_git_error_on_set_remote_origin(monkeypatch: Any) -> None:
    def raise_remote_origin_error(
        self: GitExporter, path_to_local_files: str, job: Job
    ) -> None:
        raise GitRemoteOriginError("")

    monkeypatch.setattr(GitExporter, "git_command_init_repo", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_add_all_files", mock_command_success)
    monkeypatch.setattr(
        GitExporter, "git_command_add_initial_commit", mock_command_success
    )
    monkeypatch.setattr(
        GitExporter, "git_command_set_remote_origin", raise_remote_origin_error
    )


@pytest.fixture
def mock_git_error_on_push(monkeypatch: Any) -> None:
    def raise_push_error(self: GitExporter, path_to_local_files: str) -> None:
        raise GitPushError("")

    monkeypatch.setattr(GitExporter, "git_command_init_repo", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_add_all_files", mock_command_success)
    monkeypatch.setattr(
        GitExporter, "git_command_add_initial_commit", mock_command_success
    )
    monkeypatch.setattr(
        GitExporter, "git_command_set_remote_origin", mock_command_success
    )
    monkeypatch.setattr(GitExporter, "git_command_set_branch", mock_command_success)
    monkeypatch.setattr(GitExporter, "git_command_push_to_remote", raise_push_error)


@pytest.mark.usefixtures("mock_git_success")
def test_git_exporter(
    db: Session,
    basic_job: dict,
) -> None:

    job = basic_job["db_job"]

    assert job

    exporter = GitExporter(db, job_id=job.id)

    exporter.process()

    # Check that the exporting process started and we have the log entry
    exporting_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.EXPORTING).one()
    )
    assert exporting_status_log

    # Check that the exporting process finished and we moved to exporting successfully
    exporting_successfully_status_log = (
        db.query(JobLog)
        .filter_by(
            job_id=job.id,
            from_status=JobStatus.EXPORTING,
            to_status=JobStatus.EXPORTING_SUCCESSFULLY,
        )
        .one()
    )
    assert exporting_successfully_status_log

    # Check that the whole process finished and we the final status is FINISHED_SUCCESSFULLY
    finished_successfully_status_log = (
        db.query(JobLog)
        .filter_by(
            job_id=job.id,
            from_status=JobStatus.EXPORTING_SUCCESSFULLY,
            to_status=JobStatus.FINISHED_SUCCESSFULLY,
        )
        .one()
    )
    assert finished_successfully_status_log

    # Check that the status of the job if FINISHED_SUCCESSFULLY
    retrieved_job = (
        db.query(Job)
        .filter_by(
            id=job.id,
        )
        .one()
    )
    assert retrieved_job.status == JobStatus.FINISHED_SUCCESSFULLY


# Test what happens if we found an error in the commit step
@pytest.mark.usefixtures("mock_git_error_on_set_remote_origin")
def test_git_exporter_error_on_commit(db: Session, basic_job: dict) -> None:

    job = basic_job["db_job"]
    assert job

    exporter = GitExporter(db, job_id=job.id)
    exporter.process()

    retrieved_job = (
        db.query(Job)
        .filter_by(
            id=job.id,
        )
        .one()
    )
    assert retrieved_job.status == JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE


# Test what happens if we found an error in the commit step
@pytest.mark.usefixtures("mock_git_error_on_push")
def test_git_exporter_error_on_push(db: Session, basic_job: dict) -> None:

    job = basic_job["db_job"]
    assert job

    exporter = GitExporter(db, job_id=job.id)
    exporter.process()

    retrieved_job = (
        db.query(Job)
        .filter_by(
            id=job.id,
        )
        .one()
    )
    assert retrieved_job.status == JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE
