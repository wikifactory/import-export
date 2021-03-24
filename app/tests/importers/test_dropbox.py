import datetime
import os
import pathlib
from typing import Any, Dict, Generator, List, Optional

import pytest
from dropbox.dropbox_client import Dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata, FolderMetadata
from sqlalchemy.orm import Session

from app import crud
from app.core.config import settings
from app.importers import dropbox
from app.importers.dropbox import DropboxImporter
from app.models.job import Job, JobStatus
from app.schemas import JobCreate
from app.tests.utils import utils


class DropbboxListFolderMock:  # Imitates ListFolderResult
    entries: Optional[List]
    has_more: bool = False


@pytest.fixture(scope="function")
def basic_job(db: Session) -> Generator[Dict, None, None]:
    random_project_name = utils.random_lower_string()
    job_input = JobCreate(
        import_service="dropbox",
        import_url="https://www.dropbox.com/home/user_folder",
        export_service="wikifactory",
        export_url=f"https://wikifactory.com/@user/{random_project_name}",
        import_token="import_token",
    )
    db_job = crud.job.create(db, obj_in=job_input)

    db_job.path = os.path.join(settings.JOBS_BASE_PATH, "sample-project")

    yield {
        "job_input": job_input,
        "db_job": db_job,
        "project_name": random_project_name,
    }
    crud.job.remove(db, id=db_job.id)


@pytest.fixture
def dropbox_mock(monkeypatch: Any, remote_data: dict) -> None:
    def mock_files_list_folder(
        self: Any, path: str, shared_link: str = None
    ) -> DropbboxListFolderMock:
        files_list = DropbboxListFolderMock()

        if path != "":
            files_list.entries = remote_data[path].get("children", [])
        else:
            files_list.entries = remote_data[shared_link].get("children", [])
        return files_list

    def mock_dropbox_handler(self: Any, oauth2_access_token: str) -> dropbox.Dropbox:
        return dropbox.Dropbox(oauth2_access_token)

    monkeypatch.setattr(Dropbox, "files_list_folder", mock_files_list_folder)
    monkeypatch.setattr(dropbox, "Dropbox", mock_dropbox_handler)


@pytest.fixture
def download_mock(monkeypatch: Any, basic_job: dict) -> None:
    def mock_files_download_to_file(
        self: Any, download_path: str, remote_path: str
    ) -> None:
        with open(download_path, "wb") as file_handle:
            file_handle.write(b"dummycontent")

    monkeypatch.setattr(Dropbox, "files_download_to_file", mock_files_download_to_file)


@pytest.mark.parametrize(
    "remote_data, expected_tree",
    [
        (
            {
                "root-folder": {
                    "entry": FolderMetadata(id="root-folder"),
                    "children": [
                        FileMetadata(
                            id="root-file-1",
                            name="README.md",
                            size=0,
                            server_modified=datetime.datetime(2020, 1, 1),
                            client_modified=datetime.datetime(2020, 1, 1),
                            rev="123456789",
                        ),
                        FolderMetadata(id="subfolder-1", name="Subfolder"),
                    ],
                },
                "subfolder-1": {
                    "children": [
                        FileMetadata(
                            id="nested-file-1",
                            name="test.txt",
                            size=0,
                            server_modified=datetime.datetime(2020, 1, 1),
                            client_modified=datetime.datetime(2020, 1, 1),
                            rev="123456789",
                        ),
                    ],
                },
            },
            {
                "README.md": {
                    "entry": FileMetadata(
                        id="root-file-1",
                        name="README.md",
                        size=0,
                        server_modified=datetime.datetime(2020, 1, 1),
                        client_modified=datetime.datetime(2020, 1, 1),
                        rev="123456789",
                    ),
                    "children": {},
                },
                "Subfolder": {
                    "entry": FolderMetadata(id="subfolder-1", name="Subfolder"),
                    "children": {
                        "test.txt": {
                            "entry": FileMetadata(
                                id="nested-file-1",
                                name="test.txt",
                                size=0,
                                server_modified=datetime.datetime(2020, 1, 1),
                                client_modified=datetime.datetime(2020, 1, 1),
                                rev="123456789",
                            ),
                            "children": {},
                        }
                    },
                },
            },
        )
    ],
)
@pytest.mark.usefixtures("dropbox_mock")
def test_build_tree_recursively(
    db: Session, basic_job: dict, expected_tree: dict
) -> None:
    importer = DropboxImporter(db, basic_job["db_job"].id)
    importer.url_type = "user_folder"
    importer.dropbox_handler = Dropbox(oauth2_access_token="sadas")
    tree: Dict = {}
    importer.build_tree_recursively(tree, "root-folder")

    assert tree == expected_tree


@pytest.fixture
def remote_data(basic_job: Dict) -> Dict:

    return {
        "/user_folder": {
            "entry": FolderMetadata(id="user_folder"),
            "children": [
                FileMetadata(
                    id="root-file-1",
                    name="README.md",
                    size=0,
                    server_modified=datetime.datetime(2020, 1, 1),
                    client_modified=datetime.datetime(2020, 1, 1),
                    rev="123456789",
                ),
                FolderMetadata(id="subfolder-1", name="Subfolder"),
            ],
        },
        "subfolder-1": {
            "children": [
                FileMetadata(
                    id="nested-file-1",
                    name="test.txt",
                    size=0,
                    server_modified=datetime.datetime(2020, 1, 1),
                    client_modified=datetime.datetime(2020, 1, 1),
                    rev="123456789",
                ),
            ],
        },
        "total_items": 2,
    }


def assert_tree_directory_recursive(current_level: Dict, accumulated_path: str) -> None:
    for (name, node) in current_level.items():
        check_path = os.path.join(accumulated_path, name)
        entry = node.get("entry")
        if isinstance(entry, FolderMetadata):
            assert os.path.isdir(check_path)
            children = node.get("children")
            assert_tree_directory_recursive(children, check_path)
        else:
            assert os.path.isfile(check_path)


@pytest.mark.usefixtures("dropbox_mock", "download_mock")
def test_dropbox_importer_success(
    tmpdir: pathlib.Path, db: Session, basic_job: dict, remote_data: Dict
) -> None:
    job: Job = basic_job["db_job"]
    job.path = str(tmpdir)

    importer = DropboxImporter(db, job.id)
    importer.process()

    importer.tree_root["entry"] = None

    assert_tree_directory_recursive(
        importer.tree_root["children"], basic_job["db_job"].path
    )

    assert job.imported_items == remote_data["total_items"]

    assert job.status is JobStatus.IMPORTING_SUCCESSFULLY


@pytest.fixture
def launch_api_error(monkeypatch: Any, exception: Exception) -> None:
    def mock_api_exception(*args: List, **kwargs: Dict) -> None:
        raise exception

    monkeypatch.setattr(Dropbox, "files_list_folder", mock_api_exception)
    monkeypatch.setattr(dropbox, "Dropbox", mock_api_exception)


@pytest.mark.parametrize(
    "exception, job_status",
    [
        (
            ApiError(
                request_id="id",
                user_message_text="",
                user_message_locale="",
                error=None,
            ),
            JobStatus.IMPORTING_ERROR_DATA_UNREACHABLE,
        ),
        (
            AuthError(request_id="id", error=None),
            JobStatus.IMPORTING_ERROR_AUTHORIZATION_REQUIRED,
        ),
    ],
)
@pytest.mark.usefixtures("launch_api_error")
def test_dropbox_importer_api_error(
    db: Session, basic_job: dict, exception: Exception, job_status: JobStatus
) -> None:
    job = basic_job["db_job"]
    importer = DropboxImporter(db, job.id)
    importer.process()
    assert job.status is job_status
