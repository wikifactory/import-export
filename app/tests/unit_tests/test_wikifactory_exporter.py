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

from app.models import add_job_to_db
from app.model.manifest import Manifest
from app.model.element import Element, ElementType

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


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


@pytest.mark.parametrize(
    "file_path, project_details, expected_headers",
    [
        (
            f"{CURRENT_DIR}/test_files/sample-project/README.md",
            {
                "space_id": "space-id",
                "project_id": "project-id",
                "private": False,
            },
            {"x-amz-acl": "public-read", "Content-Type": "text/plain"},
        ),
        (
            f"{CURRENT_DIR}/test_files/sample-project/README.md",
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
    monkeypatch, exporter, file_path, project_details, expected_headers
):
    def mock_put_assert_headers(*args, **kwargs):
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


def test_upload_file_error(monkeypatch, exporter):
    def mock_put_status_error(*args, **kwargs):
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
    file_path = f"{CURRENT_DIR}/test_files/sample-project/README.md"

    with open(file_path, "rb") as file_handle, pytest.raises(
        error.FileUploadError
    ):
        exporter.upload_file(file_handle, file_url)


@pytest.mark.parametrize(
    "project_details, file_id, expected_variables",
    [
        (
            {"space_id": "space-id", "project_id": "project-id"},
            "file-id",
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
def test_complete_file_mutation_variables(
    monkeypatch,
    exporter,
    project_details,
    file_id,
    expected_variables,
):
    exporter.project_details = project_details
    dummy_file_data = {
        "file": {
            "file": {
                "id": file_id,
            }
        }
    }
    mock_gql_response(
        monkeypatch,
        response_dict={"data": dummy_file_data},
        expected_variables=expected_variables,
    )
    exporter.complete_file(file_id)


@pytest.mark.parametrize(
    "project_path, project_details, element, file_id, expected_variables",
    [
        (
            f"{CURRENT_DIR}/test_files/sample-project",
            {"space_id": "space-id", "project_id": "project-id"},
            Element(path=f"{CURRENT_DIR}/test_files/sample-project/README.md"),
            "file-id",
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
def test_perform_operation_mutation_variables(
    monkeypatch,
    exporter,
    project_path,
    project_details,
    element,
    file_id,
    expected_variables,
):
    exporter.project_path = project_path
    exporter.project_details = project_details
    dummy_operation_data = {
        "operation": {
            "project": {
                "id": project_details.get("project_id"),
            }
        }
    }
    mock_gql_response(
        monkeypatch,
        response_dict={"data": dummy_operation_data},
        expected_variables=expected_variables,
    )
    exporter.perform_mutation_operation(element, file_id)


@pytest.mark.parametrize(
    "project_details, expected_variables",
    [
        (
            {"space_id": "space-id", "project_id": "project-id"},
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
def test_on_finished_cb_mutation_variables(
    monkeypatch,
    exporter,
    project_details,
    expected_variables,
):
    exporter.project_details = project_details
    dummy_commit_data = {
        "commit": {
            "project": {
                "id": project_details.get("project_id"),
            }
        }
    }
    mock_gql_response(
        monkeypatch,
        response_dict={"data": dummy_commit_data},
        expected_variables=expected_variables,
    )
    exporter.on_finished_cb()


def test_on_file_cb_user_errors(monkeypatch, exporter):
    def mock_process_element(*args, **kwargs):
        raise error.WikifactoryAPIUserErrors()

    monkeypatch.setattr(exporter, "process_element", mock_process_element)

    with pytest.raises(error.FileUploadError):
        exporter.on_file_cb(Element())


def test_on_file_cb_no_file_id(monkeypatch, exporter):
    def mock_process_element(*args, **kwargs):
        return {"id": None, "uploadUrl": None}

    monkeypatch.setattr(exporter, "process_element", mock_process_element)

    with pytest.raises(error.FileUploadError):
        exporter.on_file_cb(Element())


@pytest.mark.parametrize("manifest", [None, Manifest()])
def test_export_manifest_invalid(monkeypatch, exporter, manifest):
    def mock_get_project_details(*args, **kwargs):
        return {
            "space_id": "space-id",
            "project_id": "project-id",
            "private": False,
        }

    monkeypatch.setattr(
        exporter, "get_project_details", mock_get_project_details
    )

    with pytest.raises(error.NotValidManifest):
        exporter.export_manifest(manifest)


@pytest.mark.parametrize(
    "manifest",
    [
        Manifest(
            project_id="project-id",
            project_name="Test Project",
            project_description="This is a test project",
            source_url="https://github.com/wikifactory/sample-project",
            elements=[
                Element(
                    id="element-id",
                    type=ElementType.FILE,
                    name="README.md",
                    path=f"{CURRENT_DIR}/test_files/sample-project/README.md",
                )
            ],
        )
    ],
)
def test_export_manifest(monkeypatch, exporter, manifest):
    def mock_get_project_details(*args, **kwargs):
        return {
            "space_id": "space-id",
            "project_id": "project-id",
            "private": False,
        }

    def mock_iterate_through_elements(*args, **kwargs):
        pass

    monkeypatch.setattr(
        exporter, "get_project_details", mock_get_project_details
    )
    monkeypatch.setattr(
        manifest, "iterate_through_elements", mock_iterate_through_elements
    )

    result = exporter.export_manifest(manifest)
    assert exporter.manifest is manifest
    assert result.get("exported") == "true"
    assert result.get("manifest") == manifest.toJson()
