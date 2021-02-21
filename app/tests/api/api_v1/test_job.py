import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.models.job import JobStatus
from app.schemas.job import JobCreate


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


def test_get_job(db: Session, client: TestClient) -> None:
    job_create = JobCreate(
        import_url="https://github.com/wikifactory/job-progress",
        import_service="git",
        export_url="https://wikifactory.com/+wikifactory/job-progress",
        export_service="wikifactory",
    )
    db_job = crud.job.create(db, obj_in=job_create)
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
def test_retry_job(
    db: Session, client: TestClient, job_create: JobCreate, status: JobStatus
) -> None:
    db_job = crud.job.create(db, obj_in=job_create)
    crud.job.update_status(db, db_obj=db_job, status=status)
    response = client.post(f"{settings.API_V1_STR}/job/{db_job.id}/retry")
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
    response = client.post(f"{settings.API_V1_STR}/job/{job_id}/retry")
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
