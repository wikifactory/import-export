import os
from typing import Any, Dict, Generator, List

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.job import JobStatus
from app.schemas.job import JobCreate
from app.tests.utils import utils


@pytest.fixture
def dummy_process_job(monkeypatch: Any) -> None:
    def send_task_mock(*args: List, **kwargs: Dict) -> None:
        pass

    monkeypatch.setattr(celery_app, "send_task", send_task_mock)


@pytest.fixture
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


@pytest.mark.parametrize(
    "data",
    [
        {
            "import_url": "https://github.com/wikifactory/sample-1",
            "export_url": "https://wikifactory.com/+wikifactory/sample-1",
            "import_service": "git",
            "export_service": "wikifactory",
        },
        {
            "import_url": "https://github.com/wikifactory/sample-2",
            "export_url": "https://wikifactory.com/+wikifactory/sample-2",
            "import_service": "git",
            "export_service": "wikifactory",
            "import_token": "github-token",
            "export_token": "wikifactory-token",
        },
    ],
)
@pytest.mark.usefixtures("dummy_process_job")
def test_post_job(client: TestClient, data: dict) -> None:
    response = client.post(f"{settings.API_V1_STR}/job/", json=data)
    assert response.status_code == requests.codes["ok"]
    new_job = response.json()
    assert new_job
    assert new_job.get("status") == JobStatus.PENDING.value
    assert new_job.get("import_url") == data.get("import_url")
    assert new_job.get("import_service") == data.get("import_service")
    assert new_job.get("import_token") == data.get("import_token")
    assert new_job.get("export_url") == data.get("export_url")
    assert new_job.get("export_service") == data.get("export_service")
    assert new_job.get("export_token") == data.get("export_token")


@pytest.mark.parametrize(
    "data, status_code",
    [
        (
            {
                "import_url": "https://github.com/wikifactory/source",
                "import_service": "git",
                "export_url": "https://wikifactory.com/+wikifactory/target",
                "export_service": "wikifactory",
            },
            requests.codes["conflict"],
        )
    ],
)
def test_post_job_error(
    db: Session, client: TestClient, data: dict, status_code: int
) -> None:
    job_create = JobCreate(
        import_url="https://github.com/wikifactory/source",
        import_service="git",
        export_url="https://wikifactory.com/+wikifactory/target",
        export_service="wikifactory",
    )
    crud.job.create(db, obj_in=job_create)
    response = client.post(f"{settings.API_V1_STR}/job/", json=data)
    assert response.status_code == status_code


# FIXME - generate more test cases
@pytest.mark.parametrize(
    "status, item_data, expected_progress",
    [
        (JobStatus.PENDING, None, {"general": 0, "status": 0}),
        (JobStatus.IMPORTING, None, {"general": 0.25, "status": 0}),
        (
            JobStatus.IMPORTING,
            {"total": 2, "imported": 1},
            {"general": 0.25, "status": 0.5},
        ),
        (JobStatus.EXPORTING, None, {"general": 0.75, "status": 0}),
        (
            JobStatus.EXPORTING,
            {"total": 2, "exported": 1},
            {"general": 0.75, "status": 0.5},
        ),
    ],
)
def test_get_job(
    db: Session,
    basic_job: dict,
    client: TestClient,
    status: JobStatus,
    item_data: dict,
    expected_progress: dict,
) -> None:
    db_job = basic_job["db_job"]
    db_job.status = status

    if item_data:
        db_job.total_items = item_data.get("total", 0)
        db_job.imported_items = item_data.get("imported", 0)
        db_job.exported_items = item_data.get("exported", 0)

    db.add(db_job)
    db.commit()
    response = client.get(f"{settings.API_V1_STR}/job/{db_job.id}")
    job = response.json()
    assert job
    assert job.get("id") == str(db_job.id)
    assert job.get("import_url") == db_job.import_url
    assert job.get("import_service") == db_job.import_service
    assert job.get("import_token") == db_job.import_token
    assert job.get("export_url") == db_job.export_url
    assert job.get("export_service") == db_job.export_service
    assert job.get("export_token") == db_job.export_token
    if expected_progress:
        assert job.get("general_progress") == expected_progress.get("general")
        assert job.get("status_progress") == expected_progress.get("status")


def test_get_job_error(client: TestClient) -> None:
    missing_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"{settings.API_V1_STR}/job/{missing_uuid}")
    assert response.status_code == requests.codes["not_found"]


# TODO - generators
@pytest.mark.parametrize(
    "job_create, status",
    [
        (
            JobCreate(
                import_url="https://github.com/wikifactory/retry-1",
                import_service="git",
                export_url="https://wikifactory.com/+wikifactory/retry-1",
                export_service="wikifactory",
            ),
            JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
        ),
    ],
)
@pytest.mark.usefixtures("dummy_process_job")
def test_retry_job(
    db: Session, client: TestClient, job_create: JobCreate, status: JobStatus
) -> None:
    db_job = crud.job.create(db, obj_in=job_create)
    crud.job.update_status(db, db_obj=db_job, status=status)
    response = client.post(f"{settings.API_V1_STR}/job/{db_job.id}/retry", json={})
    job = response.json()
    assert job
    assert job.get("id") == str(db_job.id)
    assert job.get("status") == JobStatus.PENDING.value


@pytest.mark.parametrize(
    "job_create, status, status_code",
    [
        (None, None, requests.codes["not_found"]),
        (
            JobCreate(
                import_url="https://github.com/wikifactory/retry-error-1",
                import_service="git",
                export_url="https://wikifactory.com/+wikifactory/retry-error-1",
                export_service="wikifactory",
            ),
            JobStatus.IMPORTING,
            requests.codes["unprocessable"],
        ),
    ],
)
def test_retry_job_error(
    db: Session,
    client: TestClient,
    job_create: JobCreate,
    status: JobStatus,
    status_code: int,
) -> None:
    job_id = "00000000-0000-0000-0000-000000000000"
    if job_create:
        db_job = crud.job.create(db, obj_in=job_create)
        crud.job.update_status(db, db_obj=db_job, status=status)
        job_id = db_job.id
    response = client.post(f"{settings.API_V1_STR}/job/{job_id}/retry", json={})
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "job_create, status",
    [
        (
            JobCreate(
                import_url="https://github.com/wikifactory/cancel-1",
                import_service="git",
                export_url="https://wikifactory.com/+wikifactory/cancel-1",
                export_service="wikifactory",
            ),
            JobStatus.IMPORTING,
        )
    ],
)
def test_cancel_job(
    db: Session, client: TestClient, job_create: JobCreate, status: JobStatus
) -> None:
    db_job = crud.job.create(db, obj_in=job_create)
    crud.job.update_status(db, db_obj=db_job, status=status)
    response = client.post(f"{settings.API_V1_STR}/job/{db_job.id}/cancel")
    job = response.json()
    assert job
    assert job.get("id") == str(db_job.id)
    assert job.get("status") == JobStatus.CANCELLING.value


@pytest.mark.parametrize(
    "job_create, status, status_code",
    [
        (None, None, requests.codes["not_found"]),
        (
            JobCreate(
                import_url="https://github.com/wikifactory/cancel-error-1",
                import_service="git",
                export_url="https://wikifactory.com/+wikifactory/cancel-error-1",
                export_service="wikifactory",
            ),
            JobStatus.FINISHED_SUCCESSFULLY,
            requests.codes["unprocessable"],
        ),
    ],
)
def test_cancel_job_error(
    db: Session,
    client: TestClient,
    job_create: JobCreate,
    status: JobStatus,
    status_code: int,
) -> None:
    job_id = "00000000-0000-0000-0000-000000000000"
    if job_create:
        db_job = crud.job.create(db, obj_in=job_create)
        crud.job.update_status(db, db_obj=db_job, status=status)
        job_id = db_job.id
    response = client.post(f"{settings.API_V1_STR}/job/{job_id}/cancel")
    assert response.status_code == status_code
