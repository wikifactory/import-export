import pytest

from app.models import add_job_to_db
import uuid
import oauth2client


from app.controller.importers.googledrive_importer import GoogleDriveImporter
from app.controller.importers.googledrive_errors import CredentialsNotValid


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
            def execute(self):
                return {"files": [], "nextPageToken": None}

        def list(self, q, fields):
            return self.ExecuteObject()

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


def monkeypatched_googledrive_files_fail(url, path, callbacks):
    raise oauth2client.client.AccessTokenCredentialsError


def test_googledrive_manifest_generation_success(monkeypatch, basic_job):

    monkeypatch.setattr(
        "googleapiclient.discovery.build_from_document",
        patched_googledrive_service_from_doc_success,
    )

    (job_id, details) = basic_job

    importer = GoogleDriveImporter(job_id)

    manifest = importer.process_url(details["import_url"], details["import_token"])

    assert manifest is not None
    print(manifest)


def test_googledrive_manifest_generation_fail(monkeypatch, basic_job):

    monkeypatch.setattr(
        "googleapiclient.discovery.build_from_document",
        patched_googledrive_service_from_doc_auth_error,
    )

    (job_id, details) = basic_job

    importer = GoogleDriveImporter(job_id)

    with pytest.raises(CredentialsNotValid):
        importer.process_url(details["import_url"], details["import_token"])
