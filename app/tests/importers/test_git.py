import os
import pathlib
import shutil
import subprocess
import zipfile
from distutils.dir_util import copy_tree
from typing import Any, Dict, Generator, List

import py
import pytest
from sqlalchemy.orm import Session

import app.importers.git
from app import crud
from app.importers.git import GitImporter, clone_repository
from app.models.job import JobStatus
from app.models.job_log import JobLog
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.fixture(scope="function")
def basic_job(db: Session, tmpdir: py.path.local) -> Generator[Dict, None, None]:
    random_project_name = utils.random_lower_string()
    job_input = JobCreate(
        import_service="git",
        import_url=f"https://github.com/wikifactory/{random_project_name}",
        export_service="wikifactory",
        export_url=f"https://wikifactory.com/@user/{random_project_name}",
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


@pytest.fixture()
def clone_error(monkeypatch: Any) -> None:
    def mock_clone_repository_error(*args: List, **kwargs: Dict) -> None:
        subprocess.run(["git", "clone"], check=True)

    monkeypatch.setattr(
        app.importers.git, "clone_repository", mock_clone_repository_error
    )


@pytest.fixture()
def mocked_clone_repository(monkeypatch: Any) -> None:
    def mock_clone_repository(*args: List, **kwargs: Dict) -> None:
        return

    monkeypatch.setattr(app.importers.git, "clone_repository", mock_clone_repository)


@pytest.mark.usefixtures("mocked_clone_repository")
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

This is sample-project's README file"""
    )
    assert job.manifest.source_url == job.import_url
    assert job.total_items == 1
    assert job.imported_items == job.total_items


@pytest.mark.usefixtures("clone_error")
def test_git_importer_error(db: Session, basic_job: dict) -> None:
    job = basic_job["db_job"]
    importer = GitImporter(db, job.id)
    importer.process()
    assert job.status is JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE


def test_git_clone(tmp_path: pathlib.Path) -> None:

    test_repo_file_name = "test_git_repo"

    current_dir = os.path.dirname(os.path.realpath(__file__))

    # Create a folder for the original repo that will be unzipped
    original_repo_path = tmp_path / "original_repo"
    original_repo_path.mkdir()

    # Create a folder to store the cloned files
    cloned_repo_path = tmp_path / "cloned_repo"
    cloned_repo_path.mkdir()

    test_repo_path = os.path.normpath(
        os.path.join(current_dir, "..", "test_files", f"{test_repo_file_name}.zip")
    )

    # Unzip the test_git_repo.zip file, so we can later clone it
    with zipfile.ZipFile(test_repo_path, "r") as zip_ref:
        zip_ref.extractall(original_repo_path)

    unzipped_repo_path = os.path.join(original_repo_path, test_repo_file_name)

    clone_repository(unzipped_repo_path, str(cloned_repo_path))

    # Remove the .git folder of the cloned one
    shutil.rmtree(os.path.join(cloned_repo_path, ".git"), ignore_errors=True)

    for subdir, _, files in os.walk(cloned_repo_path):
        for file in files:
            assert os.path.realpath(subdir).startswith(str(cloned_repo_path))

    # Check that the symlink has been cloned as a text file
    with open(
        os.path.join(cloned_repo_path, "hosts_links"),
    ) as f:
        assert f.read() == "/etc/hosts"
