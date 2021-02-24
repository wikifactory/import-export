import os
from typing import Any, Dict, Generator, List

import gql
import pytest
import requests
from graphql.execution import ExecutionResult
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.exporters.base import AuthRequired
from app.exporters.wikifactory import (
    FileUploadFailed,
    NoResult,
    UserErrors,
    WikifactoryExporter,
    space_slug_from_url,
    validate_url,
    wikifactory_api_request,
)
from app.models.job import JobStatus
from app.models.job_log import JobLog
from app.schemas import JobCreate
from app.tests.utils import utils


@pytest.mark.parametrize(
    "project_url, is_valid",
    [
        ("http://wikifactory.com/@botler/test-project", True),
        ("http://www.wikifactory.com/@botler/test-project", True),
        ("https://wikifactory.com/@botler/test-project", True),
        ("https://www.wikifactory.com/@botler/test-project", True),
        ("https://wikifactory.com/+wikifactory/important-project", True),
        ("https://wikifactory.com/+wikifactory/试验", True),
        ("https://wikifactory.com/+wikifactory/", False),
        ("https://wikifactory.com/+wikifactory", False),
        ("https://wikifactory.com/+/not-here", False),
        ("https://wikifactory.com/@/not-here", False),
    ],
)
def test_validate_url(project_url: str, is_valid: bool) -> None:
    assert validate_url(project_url) is is_valid


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


dummy_gql = gql.gql(
    """
    query Dummy {
      dummy {
        result
        userErrors { message, key, code }
      }
    }
    """
)


def generate_mock_gql_response(response_dict: Dict) -> ExecutionResult:
    response = requests.Response()
    response.status_code = response_dict.get("status_code") or requests.codes["ok"]
    response.raise_for_status()
    return ExecutionResult(
        data=response_dict.get("data"), errors=response_dict.get("errors")
    )


@pytest.fixture
def mock_gql_response_assert_variables(
    monkeypatch: Any, response_dict: dict, expected_variables: dict
) -> None:
    def mock_execute(*args: List, **kwargs: Dict) -> ExecutionResult:
        if expected_variables:
            assert kwargs.get("variable_values") == expected_variables

        return generate_mock_gql_response(response_dict)

    monkeypatch.setattr(gql.Client, "execute", mock_execute)


@pytest.fixture
def mock_gql_response(monkeypatch: Any, response_dict: dict) -> None:
    # mocking the response is a direct mock on the output/result
    # it doesn't use any data from the query/mutation requested
    def mock_execute(*args: List, **kwargs: Dict) -> ExecutionResult:
        return generate_mock_gql_response(response_dict)

    monkeypatch.setattr(gql.Client, "execute", mock_execute)


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


@pytest.fixture
def exporter(db: Session, basic_job: dict) -> WikifactoryExporter:
    return WikifactoryExporter(db, basic_job["db_job"].id)


@pytest.mark.parametrize(
    "response_dict",
    [
        {"status_code": requests.codes["unauthorized"]},
        {"errors": [{"message": "unauthorized request"}]},
        {"errors": [{"message": "token is invalid"}]},
        {
            "data": {
                "dummy": {
                    "userErrors": [
                        {
                            "key": 0,
                            "code": "AUTHORISATION",
                            "message": "AUTHORISATION error",
                        }
                    ]
                }
            }
        },
        {
            "data": {
                "dummy": {
                    "userErrors": [
                        {
                            "key": 0,
                            "code": "AUTHENTICATION",
                            "message": "AUTHENTICATION error",
                        }
                    ]
                }
            }
        },
        {
            "data": {
                "dummy": {
                    "userErrors": [
                        {
                            "key": 0,
                            "code": "NOTFOUND",
                            "message": "NOTFOUND error",
                        }
                    ]
                }
            }
        },
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_api_auth_error() -> None:
    with pytest.raises(AuthRequired):
        wikifactory_api_request(dummy_gql, "this-is-a-token", {}, "dummy.result")


@pytest.mark.parametrize(
    "response_dict",
    [
        {
            "data": {
                "dummy": {
                    "userErrors": [
                        {
                            "key": 0,
                            "code": "UNHANDLED_ERROR",
                            "message": "Backend exception",
                        }
                    ]
                }
            }
        },
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_api_user_error() -> None:
    with pytest.raises(UserErrors):
        wikifactory_api_request(dummy_gql, "this-is-a-token", {}, "dummy.result")


@pytest.mark.parametrize(
    "result_path, response_dict",
    [
        ("dummy", {"data": {}}),
        ("dummy.result", {"data": {"dummy": {}}}),
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_api_no_result_error(result_path: str) -> None:
    with pytest.raises(NoResult):
        wikifactory_api_request(dummy_gql, "this-is-a-token", {}, result_path)


@pytest.mark.parametrize(
    "result_path, response_dict, expected_result",
    [
        ("dummy.result", {"data": {"dummy": {"result": "ok"}}}, "ok"),
        (
            "dummy.result",
            {"data": {"dummy": {"result": [1, 2, 3]}}},
            [1, 2, 3],
        ),
        (
            "dummy.result.project",
            {"data": {"dummy": {"result": {"project": {"id": "project-id"}}}}},
            {"id": "project-id"},
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_api_success(result_path: str, expected_result: Dict) -> None:
    result = wikifactory_api_request(dummy_gql, "this-is-a-token", {}, result_path)
    assert result == expected_result


@pytest.mark.parametrize(
    "response_dict, expected_details",
    [
        (
            {
                "data": {
                    "project": {
                        "result": {
                            "id": "project-id",
                            "private": True,
                            "inSpace": {"id": "space-id"},
                        }
                    }
                }
            },
            {"project_id": "project-id", "private": True, "space_id": "space-id"},
        ),
        (
            {
                "data": {
                    "project": {
                        "result": {
                            "id": "project-id",
                            "private": False,
                            "inSpace": {"id": "space-id"},
                        }
                    }
                }
            },
            {"project_id": "project-id", "private": False, "space_id": "space-id"},
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response")
def test_get_project_details(
    exporter: WikifactoryExporter, expected_details: Dict
) -> None:
    project_details = exporter.get_project_details()
    assert project_details == expected_details


@pytest.mark.parametrize(
    "project_details, job_path, file_path, response_dict, expected_variables",
    [
        (
            {"space_id": "space-id", "project_id": "project-id"},
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project"),
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project", "README.md"),
            {
                "data": {
                    "file": {
                        "file": {
                            "id": "file-id",
                            "uploadUrl": "http://upload-domain/upload-endpoint",
                        }
                    }
                }
            },
            {
                "fileInput": {
                    "filename": "README.md",
                    "spaceId": "space-id",
                    "size": 54,
                    "projectPath": "README.md",
                    "gitHash": "19ed54249da4a5666d2617144508a897303660be",
                    "completed": False,
                    "contentType": "text/plain",
                }
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response_assert_variables")
def test_process_element_mutation_variables(
    basic_job: Dict,
    exporter: WikifactoryExporter,
    project_details: Dict,
    job_path: str,
    file_path: str,
) -> None:
    job = basic_job["db_job"]
    job.path = job_path
    exporter.project_details = project_details
    exporter.process_file(file_path)


@pytest.mark.parametrize(
    "file_path, project_details, expected_headers",
    [
        (
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project", "README.md"),
            {
                "space_id": "space-id",
                "project_id": "project-id",
                "private": False,
            },
            {"x-amz-acl": "public-read", "Content-Type": "text/plain"},
        ),
        (
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project", "README.md"),
            {
                "space_id": "space-id",
                "project_id": "project-id",
                "private": True,
            },
            {"x-amz-acl": "private", "Content-Type": "text/plain"},
        ),
    ],
)
def test_upload_file_headers(
    monkeypatch: Any,
    exporter: WikifactoryExporter,
    file_path: str,
    project_details: Dict,
    expected_headers: Dict,
) -> None:
    def mock_put_assert_headers(*args: List, **kwargs: Dict) -> requests.Response:
        headers = kwargs.get("headers")
        assert headers == expected_headers
        response = requests.Response()
        response.status_code = requests.codes["ok"]
        return response

    monkeypatch.setattr(requests, "put", mock_put_assert_headers)

    exporter.project_details = project_details

    file_url = "http://upload-domain/upload-endpoint"

    with open(file_path, "rb") as file_handle:
        exporter.upload_file(file_handle, file_url)


def test_upload_file_error(monkeypatch: Any, exporter: WikifactoryExporter) -> None:
    def mock_put_status_error(*args: List, **kwargs: Dict) -> requests.Response:
        response = requests.Response()
        response.status_code = requests.codes["expectation_failed"]
        return response

    monkeypatch.setattr(requests, "put", mock_put_status_error)

    exporter.project_details = {
        "space_id": "space-id",
        "project_id": "project-id",
        "private": False,
    }

    file_url = "http://upload-domain/upload-endpoint"
    file_path = os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project", "README.md")

    with open(file_path, "rb") as file_handle, pytest.raises(FileUploadFailed):
        exporter.upload_file(file_handle, file_url)


@pytest.mark.parametrize(
    "project_details, file_id, response_dict, expected_variables",
    [
        (
            {"space_id": "space-id", "project_id": "project-id"},
            "file-id",
            {
                "data": {
                    "file": {
                        "file": {
                            "id": "file-id",
                        }
                    }
                }
            },
            {
                "fileInput": {
                    "id": "file-id",
                    "spaceId": "space-id",
                    "completed": True,
                }
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response_assert_variables")
def test_complete_file_mutation_variables(
    exporter: WikifactoryExporter, project_details: Dict, file_id: str
) -> None:
    exporter.project_details = project_details
    exporter.complete_file(file_id)


@pytest.mark.parametrize(
    "project_path, project_details, file_path, file_id, response_dict, expected_variables",
    [
        (
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project"),
            {"space_id": "space-id", "project_id": "project-id"},
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project", "README.md"),
            "file-id",
            {
                "data": {
                    "operation": {
                        "project": {
                            "id": "project-id",
                        }
                    }
                }
            },
            {
                "operationData": {
                    "fileId": "file-id",
                    "opType": "ADD",
                    "path": "README.md",
                    "projectId": "project-id",
                }
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response_assert_variables")
def test_perform_mutation_operation_variables(
    basic_job: Dict,
    exporter: WikifactoryExporter,
    project_path: str,
    project_details: Dict,
    file_id: str,
    file_path: str,
) -> None:
    job = basic_job["db_job"]
    job.path = project_path
    exporter.project_details = project_details
    exporter.perform_mutation_operation(file_path, file_id)


@pytest.mark.parametrize(
    "project_details, response_dict, expected_variables",
    [
        (
            {"space_id": "space-id", "project_id": "project-id"},
            {
                "data": {
                    "commit": {
                        "project": {
                            "id": "project-id",
                        }
                    }
                }
            },
            {
                "commitData": {
                    "projectId": "project-id",
                    "title": "Import files",
                    "description": "",
                }
            },
        ),
    ],
)
@pytest.mark.usefixtures("mock_gql_response_assert_variables")
def test_on_finished_cb_mutation_variables(
    exporter: WikifactoryExporter, project_details: Dict
) -> None:
    exporter.project_details = project_details
    exporter.on_finished_cb()


def test_on_file_cb_user_errors(
    monkeypatch: Any, exporter: WikifactoryExporter
) -> None:
    def mock_process_file(*args: List, **kwargs: Dict) -> None:
        raise UserErrors()

    monkeypatch.setattr(exporter, "process_file", mock_process_file)

    with pytest.raises(FileUploadFailed):
        exporter.on_file_cb("")


def test_on_file_cb_no_file_id(monkeypatch: Any, exporter: WikifactoryExporter) -> None:
    def mock_process_file(*args: List, **kwargs: Dict) -> Dict:
        return {"id": None, "uploadUrl": None}

    monkeypatch.setattr(exporter, "process_file", mock_process_file)

    with pytest.raises(FileUploadFailed):
        exporter.on_file_cb("")


@pytest.mark.parametrize(
    "job_path, project_details",
    [
        (
            os.path.join(settings.DOWNLOAD_BASE_PATH, "sample-project"),
            {"project_id": "project-id", "private": True, "space_id": "space-id"},
        )
    ],
)
def test_wikifactory_exporter(
    monkeypatch: Any,
    db: Session,
    project_details: dict,
    basic_job: dict,
    exporter: WikifactoryExporter,
    job_path: str,
) -> None:
    def mock_get_project_details(*args: List, **kwargs: Dict) -> Dict:
        return project_details

    monkeypatch.setattr(exporter, "get_project_details", mock_get_project_details)

    def mock_on_file_cb(*args: List, **kwargs: Dict) -> None:
        pass

    monkeypatch.setattr(exporter, "on_file_cb", mock_on_file_cb)

    def mock_on_finished_cb(*args: List, **kwargs: Dict) -> None:
        pass

    monkeypatch.setattr(exporter, "on_finished_cb", mock_on_finished_cb)

    job = basic_job["db_job"]
    job.path = job_path
    exporter.process()

    # TODO check that on_file_cb has been called for each file

    # TODO check that on_finished_cb has been called

    # check log
    exporting_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.EXPORTING).one()
    )
    assert exporting_status_log
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
