import os
from typing import Any, Dict, Generator, List

import gql
import py
import pytest
import requests
from gql import Client
from requests.models import Response
from sqlalchemy.orm import Session

from app import crud
from app.importers.wikifactory import WikifactoryImporter, space_slug_from_url
from app.models.job import JobStatus
from app.models.job_log import JobLog
from app.models.manifest import Manifest
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.mark.parametrize(
    "project_url, space, slug",
    [
        (
            "http://wikifactory.com/@botler/test-project",
            "@botler",
            "test-project",
        ),
        ("http://wikifactory.com/+wikifactory/试验", "+wikifactory", "试验"),
    ],
)
def test_space_slug_from_url(project_url: str, space: str, slug: str) -> None:
    result = space_slug_from_url(project_url)
    assert result.get("space") == space
    assert result.get("slug") == slug


def generate_mock_gql_response(client: Client, response_dict: Dict) -> Dict:
    response = requests.Response()
    response.status_code = response_dict.get("status_code") or requests.codes["ok"]
    response.raise_for_status()

    errors = response_dict.get("errors")
    if errors:
        raise Exception(str(errors[0]))

    return response_dict.get("data", {})


@pytest.fixture
def mock_gql_response_assert_variables(
    monkeypatch: Any, response_dict: dict, expected_variables: dict
) -> None:
    def mock_execute(self: Client, *args: List, **kwargs: Dict) -> Dict:
        if expected_variables:
            assert kwargs.get("variable_values") == expected_variables

        return generate_mock_gql_response(self, response_dict)

    monkeypatch.setattr(gql.Client, "execute", mock_execute)


@pytest.fixture
def mock_gql_response(monkeypatch: Any, response_dict: dict) -> None:
    # mocking the response is a direct mock on the output/result
    # it doesn't use any data from the query/mutation requested
    def mock_execute(self: Client, *args: List, **kwargs: Dict) -> Dict:
        return generate_mock_gql_response(self, response_dict)

    monkeypatch.setattr(gql.Client, "execute", mock_execute)


@pytest.fixture
def basic_job(db: Session, tmpdir: py.path.local) -> Generator[Dict, None, None]:
    random_project_name = utils.random_lower_string()
    job_input = JobCreate(
        import_service="wikifactory",
        import_url=f"https://wikifactory.com/@usersource/{random_project_name}",
        export_service="git",
        export_url="https://github.com/user/repo",
    )
    db_job = crud.job.create(db, obj_in=job_input)

    db_job.path = os.path.join(tmpdir, str(db_job.id))

    yield {
        "job_input": job_input,
        "db_job": db_job,
        "project_name": random_project_name,
    }
    crud.job.remove(db, id=db_job.id)


@pytest.fixture
def importer(db: Session, basic_job: dict) -> WikifactoryImporter:
    return WikifactoryImporter(db, basic_job["db_job"].id)


@pytest.mark.parametrize(
    "response_dict, expected_details",
    [
        (
            {
                "data": {
                    "project": {
                        "result": {
                            "id": "project-id",
                            "slug": "project_slug",
                            "contributionUpstream": {
                                "zipArchiveUrl": "/zipurl",
                            },
                        }
                    }
                }
            },
            {
                "project_id": "project-id",
                "slug": "project_slug",
                "zip_url": "https://wikifactory.com/zipurl",
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_get_project_details(
    importer: WikifactoryImporter, expected_details: Dict
) -> None:
    project_details = importer.get_project_details()
    assert project_details == expected_details


@pytest.mark.parametrize(
    "project_details, items_count",
    [
        (
            {
                "project_id": "project-id",
                "slug": "project_slug",
                "zip_url": "https://wikifactory.com/zipurl",
            },
            2,
        )
    ],
)
def test_wikifactory_importer(
    monkeypatch: Any,
    db: Session,
    project_details: dict,
    basic_job: dict,
    importer: WikifactoryImporter,
    items_count: int,
) -> None:
    def mock_get_project_details(*args: List, **kwargs: Dict) -> Dict:
        return project_details

    monkeypatch.setattr(importer, "get_project_details", mock_get_project_details)

    # Mock the request for the zip file
    # Instead of performing the network request, we return the content
    # of the test_zip_project file inside the test_files folder
    def mock_get_zip_from_url(*args: List, **kwargs: Dict) -> Response:
        resp: Response = Response()
        resp.status_code = 200

        current_dir = os.path.dirname(os.path.realpath(__file__))
        test_zip_file_path = os.path.normpath(
            os.path.join(current_dir, "..", "test_files", "test_zip_project.zip")
        )

        with open(test_zip_file_path, mode="rb") as file:  # b is important -> binary
            resp._content = file.read()
        return resp

    monkeypatch.setattr(requests, "get", mock_get_zip_from_url)

    job = basic_job["db_job"]

    importer.process()

    # Test the logs in the database
    pending_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.IMPORTING).one()
    )
    assert pending_status_log

    importing_status_log = (
        db.query(JobLog)
        .filter_by(job_id=job.id, to_status=JobStatus.IMPORTING_SUCCESSFULLY)
        .one()
    )
    assert importing_status_log
    importing_successfully_status_log = (
        db.query(JobLog)
        .filter_by(
            job_id=job.id,
            from_status=JobStatus.IMPORTING,
            to_status=JobStatus.IMPORTING_SUCCESSFULLY,
        )
        .one()
    )

    assert importing_successfully_status_log

    # Test downloaded files
    elements_in_project_folder = os.listdir(job.path)

    assert (len(elements_in_project_folder)) == 2

    assert "top_level_file.txt" in elements_in_project_folder
    assert "folder" in elements_in_project_folder

    nested_file = open(os.path.join(job.path, "folder", "nested_file.txt"), "r")
    assert nested_file.read() == "Nested file"

    # Test manifest content
    assert job.imported_items == items_count

    manifest = db.query(Manifest).filter_by(job_id=job.id).one()

    assert manifest
    assert manifest.project_description == ""
