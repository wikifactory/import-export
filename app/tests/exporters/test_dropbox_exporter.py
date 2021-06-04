import os
from distutils.dir_util import copy_tree
from typing import Any, Dict, Generator

import dropbox
import dropbox.files
import py
import pytest
from dropbox.exceptions import ApiError
from sqlalchemy.orm import Session

from app import crud
from app.exporters.dropbox import CHUNK_SIZE, DropboxExporter
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
        export_service="dropbox",
        export_url=f"https://www.dropbox.com/home/uploadtest/{random_project_name}",
        export_token=utils.random_lower_string(),
    )
    db_job = crud.job.create(db, obj_in=job_input)

    db_job.path = os.path.join(tmpdir, str(db_job.id))

    # Copy the content of test_files/sample-project to that path
    current_dir = os.path.dirname(os.path.realpath(__file__))
    copy_tree(
        os.path.normpath(
            os.path.join(current_dir, "..", "test_files", "sample-project")
        ),
        db_job.path,
    )

    yield {
        "job_input": job_input,
        "db_job": db_job,
        "project_name": random_project_name,
    }

    crud.job.remove(db, id=db_job.id)


@pytest.fixture
def dropbox_mock(monkeypatch: Any) -> None:
    def mock_dropbox_handler(self: Any, oauth2_access_token: str) -> dropbox.Dropbox:
        return dropbox.Dropbox(oauth2_access_token)

    monkeypatch.setattr(dropbox, "Dropbox", mock_dropbox_handler)


@pytest.fixture
def mocked_files_upload_success(monkeypatch: Any) -> None:
    def mocked_files_upload(
        self: Any, f: bytes, remote_path: str
    ) -> dropbox.files.Metadata:
        return dropbox.files.Metadata()

    monkeypatch.setattr(dropbox.Dropbox, "files_upload", mocked_files_upload)


@pytest.mark.usefixtures("mocked_files_upload_success")
def test_dropbox_exporter_success(
    db: Session,
    basic_job: dict,
) -> None:

    job = basic_job["db_job"]

    assert job

    exporter = DropboxExporter(db, job_id=job.id)

    exporter.process()

    # Check that the exporting process started and we have the log entry
    exporting_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.EXPORTING).one()
    )
    assert exporting_status_log

    # Check that the exporting process finished and we did move to exporting successfully
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

    # Check that the whole process finished and the final status is FINISHED_SUCCESSFULLY
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


@pytest.fixture
def mocked_files_upload_fail(monkeypatch: Any) -> None:
    def mocked_files_upload(self: Any, f: bytes, remote_path: str) -> ApiError:
        raise ApiError("", "", "", "")

    monkeypatch.setattr(dropbox.Dropbox, "files_upload", mocked_files_upload)


@pytest.mark.usefixtures("mocked_files_upload_fail")
def test_dropbox_upload_error(
    db: Session,
    basic_job: dict,
) -> None:

    job = basic_job["db_job"]

    assert job

    exporter = DropboxExporter(db, job_id=job.id)

    exporter.process()

    # Check that the exporting process started and we have the log entry
    exporting_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.EXPORTING).one()
    )
    assert exporting_status_log

    # Check that the exporting process failed and the new status is auth required
    exporting_error_log = (
        db.query(JobLog)
        .filter_by(
            job_id=job.id,
            from_status=JobStatus.EXPORTING,
            to_status=JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
        )
        .one()
    )
    assert exporting_error_log


@pytest.fixture
def mocked_session_upload_fail(monkeypatch: Any) -> None:
    def mocked_session_start_success(
        self: Any, f: bytes
    ) -> dropbox.files.UploadSessionStartResult:
        return dropbox.files.UploadSessionStartResult(session_id="id")

    def mocked_session_append_error(
        self: Any, f: bytes, session_id: str, offset: int
    ) -> ApiError:
        raise ApiError("", "", "", "")

    def mocked_session_uploadsessioncursor(session_id: str, offset: int) -> None:
        pass

    monkeypatch.setattr(
        dropbox.Dropbox, "files_upload_session_start", mocked_session_start_success
    )
    monkeypatch.setattr(
        dropbox.Dropbox, "files_upload_session_append", mocked_session_append_error
    )
    monkeypatch.setattr(
        dropbox.files, "UploadSessionCursor", mocked_session_uploadsessioncursor
    )

    def mocked_getsize(filename: str) -> int:
        return CHUNK_SIZE + 1

    monkeypatch.setattr(os.path, "getsize", mocked_getsize)

    # Monkeypatch the os.getsize method to force the use of the session approach


@pytest.mark.usefixtures("mocked_session_upload_fail")
def test_dropbox_upload_session_error(
    db: Session,
    basic_job: dict,
) -> None:

    job = basic_job["db_job"]

    assert job

    exporter = DropboxExporter(db, job_id=job.id)

    exporter.process()
