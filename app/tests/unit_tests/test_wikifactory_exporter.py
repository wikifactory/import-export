from app.controller.exporters.wikifactory_exporter import (
    WikifactoryExporter,
    WikifactoryMutations,
)


def get_wikifactory_api_request_result(
    wikifactory_query: str, export_token: str, variables: object
):
    if wikifactory_query == WikifactoryMutations.file_mutation.value:
        return {
            "file": {
                "id": "7f65d9567d77efc4cea3da590e8f66b0f6377521",
                "path": "/file.txt",
                "mimeType": "text/plain",
                "completed": "false",
                "slug": "@user",
            }
        }
    elif wikifactory_query == WikifactoryMutations.project_query.value:
        return {
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
        }
    elif wikifactory_query == WikifactoryMutations.operation_mutation.value:
        return ""
    elif (
        wikifactory_query == WikifactoryMutations.complete_file_mutation.value
    ):
        return ""
    elif (
        wikifactory_query
        == WikifactoryMutations.commit_contribution_mutation.value
    ):
        return ""


def test_process_element(monkeypatch):

    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        WikifactoryMutations.file_mutation.value, "", {}
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
        WikifactoryMutations.project_query.value, "", {}
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
