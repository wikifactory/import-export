import os
import shutil
from re import search

import pytest
from pydrive.drive import GoogleDrive
from pydrive.files import ApiRequestError, FileNotDownloadableError, GoogleDriveFile
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.importers.google_drive import GoogleDriveImporter, folder_mimetype, is_folder
from app.models.job import JobStatus
from app.models.job_log import JobLog
from app.schemas import JobCreate
from app.tests.utils import utils


class GoogleDriveFileListMock:
    def GetList(self):
        return [
            GoogleDriveFile(metadata=file_metadata, uploaded=True)
            for file_metadata in self.mocked_list
        ]


@pytest.fixture
def pydrive_mock(monkeypatch, remote_data: dict):
    def mock_list_file(self, param={}):
        match = search(r"'(?P<item_id>[-\w]+)'(?P<in_parents> in parents)?", param["q"])
        item_id = match.group("item_id")
        get_children = bool(match.group("in_parents"))

        list_object = GoogleDriveFileListMock()

        if get_children:
            list_object.mocked_list = remote_data[item_id].get("children", [])
        else:
            item = remote_data[item_id].get("item")
            list_object.mocked_list = [item] if item else []

        return list_object

    monkeypatch.setattr(GoogleDrive, "ListFile", mock_list_file)


@pytest.fixture
def download_mock(monkeypatch, basic_job):
    tmp_directory = basic_job["db_job"].path

    def mock_get_content(self, download_path):
        assert download_path.startswith(tmp_directory)
        with open(download_path, "wb") as file_handle:
            file_handle.write(b"dummy")

    monkeypatch.setattr(GoogleDriveFile, "GetContentFile", mock_get_content)
    yield
    shutil.rmtree(tmp_directory, ignore_errors=True)


@pytest.fixture(scope="function")
def basic_job(db: Session) -> dict:
    random_folder_id = utils.random_lower_string()
    job_input = JobCreate(
        import_service="google_drive",
        import_url=f"https://drive.google.com/drive/u/0/folders/{random_folder_id}",
        export_service="wikifactory",
        export_url=f"https://wikifactory.com/@user/{random_folder_id}",
    )
    db_job = crud.job.create(db, obj_in=job_input)
    db_job.path = os.path.join(settings.DOWNLOAD_BASE_PATH, random_folder_id)
    yield {
        "job_input": job_input,
        "db_job": db_job,
        "folder_id": random_folder_id,
    }
    crud.job.remove(db, id=db_job.id)


@pytest.mark.parametrize(
    "remote_data, expected_tree",
    [
        (
            {
                "root-folder": {
                    "item": {"mimeType": folder_mimetype},
                    "children": [
                        {
                            "id": "root-file-1",
                            "title": "README.md",
                            "mimeType": "text/plain",
                        },
                        {
                            "id": "subfolder-1",
                            "title": "Subfolder",
                            "mimeType": folder_mimetype,
                        },
                    ],
                },
                "subfolder-1": {
                    "item": {"mimeType": folder_mimetype},
                    "children": [
                        {
                            "id": "nested-file-1",
                            "title": "test.txt",
                            "mimeType": "text/plain",
                        },
                    ],
                },
            },
            {
                "README.md": {
                    "item": {
                        "id": "root-file-1",
                        "title": "README.md",
                        "mimeType": "text/plain",
                    },
                    "children": {},
                },
                "Subfolder": {
                    "item": {
                        "id": "subfolder-1",
                        "title": "Subfolder",
                        "mimeType": folder_mimetype,
                    },
                    "children": {
                        "test.txt": {
                            "item": {
                                "id": "nested-file-1",
                                "title": "test.txt",
                                "mimeType": "text/plain",
                            },
                            "children": {},
                        }
                    },
                },
            },
        )
    ],
)
@pytest.mark.usefixtures("pydrive_mock")
def test_build_tree_recursively(db: Session, basic_job: dict, expected_tree: dict):
    importer = GoogleDriveImporter(db, basic_job["db_job"].id)
    importer.drive = GoogleDrive()
    tree = {}
    importer.build_tree_recursively(tree, "root-folder")
    assert tree == expected_tree


def assert_tree_directory_recursive(current_level, accumulated_path):
    for (name, node) in current_level.items():
        check_path = os.path.join(accumulated_path, name)
        item = node.get("item")
        if is_folder(item):
            assert os.path.isdir(check_path)
            children = node.get("children")
            assert_tree_directory_recursive(children, check_path)
        else:
            assert os.path.isfile(check_path)


@pytest.mark.parametrize(
    "tree",
    [
        {
            "README.md": {
                "item": GoogleDriveFile(
                    metadata={
                        "id": "root-file-1",
                        "title": "README.md",
                        "mimeType": "text/plain",
                    },
                    uploaded=True,
                ),
                "children": {},
            },
            "Subfolder": {
                "item": GoogleDriveFile(
                    metadata={
                        "id": "subfolder-1",
                        "title": "Subfolder",
                        "mimeType": folder_mimetype,
                    },
                    uploaded=True,
                ),
                "children": {
                    "test.txt": {
                        "item": GoogleDriveFile(
                            metadata={
                                "id": "nested-file-1",
                                "title": "test.txt",
                                "mimeType": "text/plain",
                            },
                            uploaded=True,
                        ),
                        "children": {},
                    }
                },
            },
        },
    ],
)
@pytest.mark.usefixtures("download_mock")
def test_download_tree_recursively(db: Session, basic_job: dict, tree: dict):
    importer = GoogleDriveImporter(db, basic_job["db_job"].id)
    importer.drive = GoogleDrive()
    importer.download_tree_recursively(tree, basic_job["db_job"].path)
    assert_tree_directory_recursive(tree, basic_job["db_job"].path)


@pytest.fixture
def remote_data(basic_job: dict):
    folder_id = basic_job["folder_id"]

    return {
        folder_id: {
            "item": {
                "id": folder_id,
                "title": "My Google Drive Project",
                "mimeType": folder_mimetype,
            },
            "children": [
                {
                    "id": "root-file-1",
                    "title": "README.md",
                    "mimeType": "text/plain",
                },
                {
                    "id": "subfolder-1",
                    "title": "Subfolder",
                    "mimeType": folder_mimetype,
                },
            ],
        },
        "subfolder-1": {
            "item": {
                "id": "subfolder-1",
                "title": "Subfolder",
                "mimeType": folder_mimetype,
            },
            "children": [
                {
                    "id": "nested-file-1",
                    "title": "test.txt",
                    "mimeType": "text/plain",
                },
            ],
        },
    }


@pytest.mark.usefixtures("pydrive_mock", "download_mock")
def test_google_drive_importer(db: Session, basic_job: dict, remote_data: dict):
    job = basic_job["db_job"]
    importer = GoogleDriveImporter(db, basic_job["db_job"].id)
    importer.process()
    assert_tree_directory_recursive(
        importer.tree_root["children"], basic_job["db_job"].path
    )
    importing_status_log = (
        db.query(JobLog).filter_by(job_id=job.id, to_status=JobStatus.IMPORTING).one()
    )
    assert importing_status_log
    assert job.status is JobStatus.IMPORTING_SUCCESSFULLY
    assert job.manifest
    assert (
        job.manifest.project_name
        == remote_data[basic_job["folder_id"]]["item"]["title"]
    )
    assert job.manifest.source_url == job.import_url


@pytest.fixture
def api_error(monkeypatch, exception: Exception):
    def mock_list_file(self, param={}):
        raise exception()

    monkeypatch.setattr(GoogleDrive, "ListFile", mock_list_file)


@pytest.mark.parametrize("exception", [ApiRequestError, FileNotDownloadableError])
@pytest.mark.usefixtures("api_error")
def test_google_drive_importer_api_error(db: Session, basic_job: dict):
    job = basic_job["db_job"]
    importer = GoogleDriveImporter(db, basic_job["db_job"].id)
    importer.process()
    assert job.status is JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE
