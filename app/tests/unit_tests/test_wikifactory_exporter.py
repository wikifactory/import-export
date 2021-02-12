import pytest
import uuid

from app.controller.exporters.wikifactory_exporter import WikifactoryExporter, validate_url
from app.controller.exporters import wikifactory_gql

from app.tests.integration_tests.test_job import create_job
from app.tests.conftest import WIKIFACTORY_TOKEN, WIKIFACTORY_TEST_PROJECT_URL
from app.models import add_job_to_db, get_job
from app.model.manifest import Manifest
from app.model.element import Element


def get_wikifactory_api_request_result(
    wikifactory_query: str = "",
    export_token: str = "",
    variables: object = {},
    result: object = {},
):
    return result


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
    ],
)
def test_validate_url(project_url, is_valid):
    assert validate_url(project_url) is is_valid


def test_process_element(monkeypatch):

    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        wikifactory_gql.file_mutation,
        "",
        {},
        result={
            "file": {
                "id": "7f65d9567d77efc4cea3da590e8f66b0f6377521",
                "path": "/file.txt",
                "mimeType": "text/plain",
                "completed": "false",
                "slug": "@user",
            }
        },
    )
    assert "file" in request_result
    assert "id" in request_result["file"]
    assert (
        request_result["file"]["id"]
        == "7f65d9567d77efc4cea3da590e8f66b0f6377521"
    )
    assert "path" in request_result["file"]
    assert request_result["file"]["path"] == "/file.txt"

    assert request_result["file"]["slug"] == "@user"


def test_project_query(monkeypatch):
    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        wikifactory_gql.project_query,
        "",
        {},
        result={
            "project": {
                "result": {
                    "id": "a590e8f66b0f63775217f65d9567d77efc4cea3d",
                    "space": {
                        "id": "de86c9ad380d87ada82e4e7a475cea5ee99308cb"
                    },
                    "inSpace": {
                        "id": "1dcb9df4f37506b7efe3f85af2ef55757a92b148"
                    },
                }
            }
        },
    )

    assert "project" in request_result

    project = request_result["project"]

    assert "result" in project
    assert (
        project["result"]["id"] == "a590e8f66b0f63775217f65d9567d77efc4cea3d"
    )
    assert (
        project["result"]["inSpace"]["id"]
        == "1dcb9df4f37506b7efe3f85af2ef55757a92b148"
    )
    assert (
        project["result"]["space"]["id"]
        == "de86c9ad380d87ada82e4e7a475cea5ee99308cb"
    )


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


def get_project_details_result(self, space, slug, export_token):
    # return (project_id, inspace_id)
    return (
        "a590e8f66b0f63775217f65d9567d77efc4cea3d",
        "1dcb9df4f37506b7efe3f85af2ef55757a92b148",
    )


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
