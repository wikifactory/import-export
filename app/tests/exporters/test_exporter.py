import os
from distutils.dir_util import copy_tree
from typing import Any, Dict, Generator, List

import py
import pytest
from sqlalchemy.orm import Session

from app import crud
from app.exporters.wikifactory import WikifactoryExporter
from app.models.job import Job, JobStatus
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.fixture
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


@pytest.fixture
def exporter(db: Session, basic_job: dict) -> WikifactoryExporter:
    return WikifactoryExporter(db, basic_job["db_job"].id)


@pytest.mark.parametrize(
    "project_details, items_count",
    [({"project_id": "project-id", "private": True, "space_id": "space-id"}, 1)],
)
def test_remove_files_on_finish(
    monkeypatch: Any,
    db: Session,
    project_details: dict,
    basic_job: dict,
    exporter: WikifactoryExporter,
    items_count: int,
) -> None:
    def mock_get_project_details(*args: List, **kwargs: Dict) -> Dict:
        return project_details

    monkeypatch.setattr(exporter, "get_project_details", mock_get_project_details)

    def mock_on_file_cb(*args: List, **kwargs: Dict) -> None:
        crud.job.increment_exported_items(db=db, job_id=exporter.job_id)

    monkeypatch.setattr(exporter, "on_file_cb", mock_on_file_cb)

    def mock_on_finished_cb(*args: List, **kwargs: Dict) -> None:
        pass

    monkeypatch.setattr(exporter, "on_finished_cb", mock_on_finished_cb)

    job: Job = basic_job["db_job"]

    exporter.process()

    assert job.status == JobStatus.FINISHED_SUCCESSFULLY

    assert os.path.exists(job.path) is False
