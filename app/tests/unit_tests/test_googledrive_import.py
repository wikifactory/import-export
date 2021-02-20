import pytest

from app.models import add_job_to_db
import uuid
import oauth2client


from app.controller.importers.googledrive_importer import GoogleDriveImporter
from app.controller.importers.googledrive_errors import (
    CredentialsNotValid,
    DownloadError,
)
from googleapiclient.errors import HttpError


@pytest.fixture
def basic_job():
    options = {
        "import_service": "git",
        "import_url": "https://github.com/wikifactory/sample-project",
        "import_token": None,
        "export_service": "wikifactory",
        "export_url": "https://wikifactory.com/@user/test-project",
        "export_token": "---------",
    }
    job_id = str(uuid.uuid4())
    add_job_to_db(options, job_id)
    return (job_id, options)


class FakeServiceClassSuccess:
    class FileList:
        class ExecuteObject:
            class FakeFile:
                info = {"name": "", "id": "", "mimeType": ""}

                def __init__(self, name="", id="", mimeType="text/plain"):
                    self.info["name"] = name
                    self.info["id"] = id

                def get(self, key):
                    return self.info[key]

            def execute(self):
                return {
                    "files": [self.FakeFile("testname", "testid")],
                    "nextPageToken": None,
                }

        def list(self, q, fields):
            return self.ExecuteObject()

        def get_media(self, fileId):
            pass

    def files(self):
        return self.FileList()


class FakeServiceClassFail:
    class FileList:
        class ExecuteObject:
            def execute(self):
                raise oauth2client.client.AccessTokenCredentialsError

        def list(self, q, fields):
            return self.ExecuteObject()

    def files(self):
        return self.FileList()


def patched_googledrive_service_from_doc_success(
    service,
    base,
    http,
    developerKey,
    model,
    requestBuilder,
    credentials,
    client_options,
    adc_cert_path,
    adc_key_path,
):
    return FakeServiceClassSuccess()


def patched_googledrive_service_from_doc_auth_error(
    service,
    base,
    http,
    developerKey,
    model,
    requestBuilder,
    credentials,
    client_options,
    adc_cert_path,
    adc_key_path,
):
    return FakeServiceClassFail()


def patchedMediaIOBaseDownloadSuccess(fd, request):
    class FakeDownloader:
        def next_chunk():
            return (None, True)

    return FakeDownloader


def patchedMediaIOBaseDownloadFail(fd, request):
    class FakeDownloader:
        def next_chunk():
            raise HttpError(None, b"error")

    return FakeDownloader


def monkeypatched_googledrive_files_fail(url, path, callbacks):
    raise oauth2client.client.AccessTokenCredentialsError


@pytest.fixture
def patch_build_from_doc(monkeypatch):
    monkeypatch.setattr(
        "googleapiclient.discovery.build_from_document",
        patched_googledrive_service_from_doc_success,
    )


@pytest.fixture
def patch_download_success(monkeypatch):
    # Monkeypatch the download
    monkeypatch.setattr(
        "app.controller.importers.googledrive_importer.MediaIoBaseDownload",
        patchedMediaIOBaseDownloadSuccess,
    )


@pytest.fixture
def patch_download_error(monkeypatch):
    # Monkeypatch the download
    monkeypatch.setattr(
        "app.controller.importers.googledrive_importer.MediaIoBaseDownload",
        patchedMediaIOBaseDownloadFail,
    )


def test_googledrive_manifest_generation_success(
    patch_build_from_doc, patch_download_success, basic_job
):

    (job_id, details) = basic_job

    importer = GoogleDriveImporter(job_id)

    manifest = importer.process_url(details["import_url"], details["import_token"])

    assert manifest is not None


def test_googledrive_manifest_generation_error_downloading(
    patch_build_from_doc, patch_download_error, basic_job
):

    (job_id, details) = basic_job

    importer = GoogleDriveImporter(job_id)

    with pytest.raises(DownloadError):
        _ = importer.process_url(details["import_url"], details["import_token"])


def test_googledrive_manifest_generation_credentials_not_valid(monkeypatch, basic_job):

    monkeypatch.setattr(
        "googleapiclient.discovery.build_from_document",
        patched_googledrive_service_from_doc_auth_error,
    )

    (job_id, details) = basic_job

    importer = GoogleDriveImporter(job_id)

    with pytest.raises(CredentialsNotValid):
        importer.process_url(details["import_url"], details["import_token"])
