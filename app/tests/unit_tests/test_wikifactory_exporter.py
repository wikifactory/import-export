from app.controller.exporters.wikifactory_exporter import (
    WikifactoryExporter,
    WikifactoryMutations,
)


def get_wikifactory_api_request_result(
    wikifactory_query: str,
    export_token: str,
    variables: object,
    result: object,
):
    return result


test_manifest = {
    "metatadata": {
        "date_created": "11/02/2021",
        "last_date_updated": "11/02/2021",
        "author": {
            "id": "",
            "name": "unknown-author",
            "affiliation": "",
            "email": "",
        },
        "language": "EN",
        "documentation_language": "EN",
    },
    "project_name": "test_project",
    "project_id": "",
    "project_description": "",
    "elements": [
        {
            "id": "root",
            "type": "2",
            "children": [
                {
                    "id": "index.html",
                    "type": "1",
                    "children": [],
                    "path": "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/index.html",
                    "name": "",
                },
                {
                    "id": "data.js",
                    "type": "1",
                    "children": [],
                    "path": "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/data.js",
                    "name": "",
                },
                {
                    "id": "style.css",
                    "type": "1",
                    "children": [],
                    "path": "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/style.css",
                    "name": "",
                },
                {
                    "id": "radarchart.js",
                    "type": "1",
                    "children": [],
                    "path": "/tmp/gitimports/9972e4fe-1a20-4f95-bb0c-648178b96522/radarchart.js",
                    "name": "",
                },
            ],
        }
    ],
}


def test_process_element(monkeypatch):

    monkeypatch.setattr(
        WikifactoryExporter,
        "wikifactory_api_request",
        get_wikifactory_api_request_result,
    )

    request_result = get_wikifactory_api_request_result(
        WikifactoryMutations.file_mutation.value,
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
        WikifactoryMutations.project_query.value,
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
        WikifactoryMutations.operation_mutation.value,
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
        WikifactoryMutations.complete_file_mutation.value,
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
        WikifactoryMutations.commit_contribution_mutation.value,
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
