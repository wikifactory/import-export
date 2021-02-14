import os
import pytest
import uuid
import gql
import requests
from graphql.execution import ExecutionResult

from app.controller.exporters.wikifactory_exporter import (
    WikifactoryExporter,
    validate_url,
    space_slug_from_url,
    wikifactory_api_request,
)
from app.controller import error
from app.controller.exporters import wikifactory_gql

from app.tests.integration_tests.test_job import create_job
from app.tests.conftest import WIKIFACTORY_TOKEN, WIKIFACTORY_TEST_PROJECT_URL
from app.models import add_job_to_db, get_job
from app.model.manifest import Manifest
from app.model.element import Element, ElementType

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


def get_test_manifest():

    manifest = Manifest()
    manifest.project_name = "test_project"
    manifest.project_id = "9972e4fe-1a20-4f95-bb0c-648178b96522"
    manifest.project_description = "Test description"

    root_element = Element()
    root_element.id = "root"
    root_element.type = "2"

    manifest.elements.append(root_element)

    ch_1 = Element()
    ch_1.id = "id1"
    ch_1.type = "1"
    ch_1.path = (
        "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/index.html"
    )
    ch_1.name = "index.html"

    ch_2 = Element()
    ch_2.id = "id2"
    ch_2.type = "1"
    ch_2.path = "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/main.js"
    ch_2.name = "main.js"

    root_element.children.append(ch_1)
    root_element.children.append(ch_2)

    return manifest


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
def test_validate_url(project_url, is_valid):
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
def test_space_slug_from_url(project_url, space, slug):
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


def mock_gql_response(monkeypatch, response_dict={}, expected_variables=None):
    # mocking the response is a direct mock on the output/result
    # it doesn't use any data from the query/mutation requested
    def mock_execute(*args, **kwargs):
        if expected_variables:
            assert kwargs.get("variable_values") == expected_variables

        response = requests.Response()
        response.status_code = (
            response_dict.get("status_code") or requests.codes["ok"]
        )
        response.raise_for_status()
        return ExecutionResult(
            data=response_dict.get("data"), errors=response_dict.get("errors")
        )

    monkeypatch.setattr(gql.Client, "execute", mock_execute)


@pytest.fixture
def basic_job():
    options = {
        "import_service": "git",
        "import_url": "https://github.com/wikifactory/sample-project",
        "import_token": None,
        "export_service": "wikifactory",
        "export_url": "https://wikifactory.com/@botler/sample-project",
        "export_token": "this-is-a-token",
    }
    job_id = str(uuid.uuid4())
    add_job_to_db(options, job_id)
    return job_id


@pytest.fixture
def exporter(basic_job):
    return WikifactoryExporter(basic_job)


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
def test_api_auth_error(monkeypatch, response_dict):
    mock_gql_response(monkeypatch, response_dict=response_dict)
    with pytest.raises(error.ExportAuthRequired):
        wikifactory_api_request(
            dummy_gql, "this-is-a-token", {}, "dummy.result"
        )


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
def test_api_user_error(monkeypatch, response_dict):
    mock_gql_response(monkeypatch, response_dict=response_dict)
    with pytest.raises(error.WikifactoryAPIUserErrors):
        wikifactory_api_request(
            dummy_gql, "this-is-a-token", {}, "dummy.result"
        )


def test_api_no_result_path_error(monkeypatch):
    mock_gql_response(monkeypatch, response_dict={"data": {}})
    with pytest.raises(error.WikifactoryAPINoResultPath):
        wikifactory_api_request(dummy_gql, "this-is-a-token", {}, None)


@pytest.mark.parametrize(
    "result_path,response_dict",
    [
        ("dummy", {"data": {}}),
        ("dummy.result", {"data": {"dummy": {}}}),
    ],
)
def test_api_no_result_error(monkeypatch, result_path, response_dict):
    mock_gql_response(monkeypatch, response_dict=response_dict)
    with pytest.raises(error.WikifactoryAPINoResult):
        wikifactory_api_request(dummy_gql, "this-is-a-token", {}, result_path)


@pytest.mark.parametrize(
    "result_path,response_dict,expected_result",
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
def test_api_success(monkeypatch, result_path, response_dict, expected_result):
    mock_gql_response(monkeypatch, response_dict=response_dict)

    result = wikifactory_api_request(
        dummy_gql, "this-is-a-token", {}, result_path
    )

    assert result == expected_result


@pytest.mark.parametrize(
    "project_id, private, space_id",
    [
        ("project-id", True, "space-id"),
        ("project-id", False, "space-id"),
    ],
)
def test_get_project_details(
    monkeypatch, exporter, project_id, private, space_id
):
    project_data = {
        "project": {
            "result": {
                "id": project_id,
                "private": private,
                "inSpace": {"id": space_id},
            }
        }
    }
    mock_gql_response(monkeypatch, response_dict={"data": project_data})
    project_details = exporter.get_project_details()
    assert project_details["project_id"] == project_id
    assert project_details["private"] == private
    assert project_details["space_id"] == space_id


@pytest.mark.parametrize(
    "project_path, project_details, element, expected_variables",
    [
        (
            f"{CURRENT_DIR}/test_files/sample-project",
            {"space_id": "space-id", "project_id": "project-id"},
            Element(
                path=f"{CURRENT_DIR}/test_files/sample-project/README.md",
                type=ElementType.FILE,
            ),
            {
                "fileInput": {
                    "filename": "README.md",
                    "spaceId": "space-id",
                    "size": 54,
                    "projectPath": "README.md",
                    "gitHash": "692f66f8b675de33548ce2fdb66b196e287c8971",
                    "completed": False,
                    "contentType": "text/plain",
                }
            },
        ),
    ],
)
def test_process_element_mutation_variables(
    monkeypatch,
    exporter,
    project_path,
    project_details,
    element,
    expected_variables,
):
    exporter.project_path = project_path
    exporter.project_details = project_details
    dummy_file_data = {
        "file": {
            "file": {
                "id": "file-id",
                "uploadUrl": "http://upload-domain/upload-endpoint",
            }
        }
    }
    mock_gql_response(
        monkeypatch,
        response_dict={"data": dummy_file_data},
        expected_variables=expected_variables,
    )
    exporter.process_element(element)


def test_operation_mutation(monkeypatch):
    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        wikifactory_gql.operation_mutation,
        "",
        {},
        result={"project": {"id": "a590e8f66b0f63775217f65d9567d77efc4cea3d"}},
    )

    assert "project" in request_result
    assert "id" in request_result["project"]
    assert (
        request_result["project"]["id"]
        == "a590e8f66b0f63775217f65d9567d77efc4cea3d"
    )


def test_complete_file_mutation(monkeypatch):
    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        wikifactory_gql.complete_file_mutation,
        "",
        {},
        result={
            "file": {
                "file": {
                    "id": "7f65d9567d77efc4cea3da590e8f66b0f6377521",
                    "path": "/file.txt",
                    "url": "",
                    "completed": True,
                },
                "userErrors": [],
            }
        },
    )

    assert "file" in request_result
    assert "file" in request_result["file"]
    assert len(request_result["file"]["userErrors"]) == 0

    assert "id" in request_result["file"]["file"]
    assert (
        request_result["file"]["file"]["id"]
        == "7f65d9567d77efc4cea3da590e8f66b0f6377521"
    )
    assert request_result["file"]["file"]["completed"] is True


def test_commit_contribution_mutation(monkeypatch):
    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        wikifactory_gql.commit_contribution_mutation,
        "",
        {},
        result={
            "commit": {
                "project": {
                    "id": "a590e8f66b0f63775217f65d9567d77efc4cea3d",
                    "contributionCount": 1,
                    "inSpace": {
                        "id": "1dcb9df4f37506b7efe3f85af2ef55757a92b148"
                    },
                },
                "userErrors": [],
            }
        },
    )

    assert "commit" in request_result
    assert "project" in request_result["commit"]
    assert len(request_result["commit"]["userErrors"]) == 0

    assert "id" in request_result["commit"]["project"]
    assert (
        request_result["commit"]["project"]["id"]
        == "a590e8f66b0f63775217f65d9567d77efc4cea3d"
    )


def get_file_mutation_result(
    self, element, file_name, project_path, export_token
):

    return {
        "file": {
            "file": {
                "id": element.id,
                "path": element.path,
                "completed": False,
                "uploadUrl": "www.testurl.com",
            },
            "userErrors": [],
        }
    }


def upload_file_result(self, local_path, file_url):
    pass


def get_complete_file_mutation_result(self, space_id, file_id, export_token):
    return {
        "file": {
            "file": {
                "id": "7f65d9567d77efc4cea3da590e8f66b0f6377521",
                "path": "/file.txt",
                "url": "",
                "completed": True,
            },
            "userErrors": [],
        }
    }


def get_perform_mutation_operation_result(
    self, element, file_id, project_path, export_token
):
    return {"project": {"id": "a590e8f66b0f63775217f65d9567d77efc4cea3d"}}


def get_commit_contribution_result(self, export_token):
    return {
        "commit": {
            "project": {
                "id": "a590e8f66b0f63775217f65d9567d77efc4cea3d",
                "contributionCount": 1,
                "inSpace": {"id": "1dcb9df4f37506b7efe3f85af2ef55757a92b148"},
            },
            "userErrors": [],
        }
    }


def test_export_from_manifest(monkeypatch):

    monkeypatch.setattr(
        WikifactoryExporter,
        "process_element",
        get_file_mutation_result,
    )

    monkeypatch.setattr(
        WikifactoryExporter,
        "upload_file",
        upload_file_result,
    )

    monkeypatch.setattr(
        WikifactoryExporter,
        "get_project_details",
        get_project_details_result,
    )

    monkeypatch.setattr(
        WikifactoryExporter,
        "perform_mutation_operation",
        get_perform_mutation_operation_result,
    )

    monkeypatch.setattr(
        WikifactoryExporter,
        "complete_file",
        get_complete_file_mutation_result,
    )

    monkeypatch.setattr(
        WikifactoryExporter,
        "commit_contribution",
        get_commit_contribution_result,
    )

    # Create the exporting job
    (job_id, job) = create_job(
        import_url="https://github.com/rievo/icosphere",
        import_service="git",
        export_url=WIKIFACTORY_TEST_PROJECT_URL,
        export_service="wikifactory",
        export_token=WIKIFACTORY_TOKEN,
    )

    # Add the job to the db
    add_job_to_db(job, job_id)

    wfexporter = WikifactoryExporter(job_id)
    result = wfexporter.export_manifest(
        get_test_manifest(), job["export_url"], job["export_token"]
    )

    assert result is not None

    retrieved_job = get_job(job_id)

    assert retrieved_job is not None
