import pytest
import requests
from fastapi.testclient import TestClient

from app.core.config import settings
from app.tests.utils import utils


@pytest.mark.parametrize(
    "data, service_name",
    [
        ({"url": "https://github.com/wikifactory/sample-project"}, "git"),
        (
            {
                "url": f"https://drive.google.com/drive/u/0/folders/{utils.random_lower_string()}"
            },
            "google_drive",
        ),
        ({"url": "https://wikifactory.com/+wikifactory/sample-project"}, "wikifactory"),
        ({"url": "https://wikifactory.com/@user/sample-project"}, "wikifactory"),
        ({"url": "https://www.thingiverse.com/thing:1234567"}, "unknown"),
    ],
)
def test_validate_service(client: TestClient, data: dict, service_name: str) -> None:
    response = client.post(f"{settings.API_V1_STR}/service/validate", json=data)
    assert response.status_code == requests.codes["ok"]
    validation = response.json()
    assert validation
    assert validation.get("name") == service_name
