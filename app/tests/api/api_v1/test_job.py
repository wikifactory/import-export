from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.job import JobStatus


def test_post_job(client: TestClient) -> None:
    data = {
        "import_url": "url",
        "export_url": "url",
        "import_service": "service",
        "export_service": "service",
        "import_token": "import-token",
        "export_token": "import-token",
    }
    respose = client.post(f"{settings.API_V1_STR}/job/", json=data)
    new_job = respose.json()
    assert new_job
    assert new_job.status == JobStatus.PENDING.value
