from app.controller.importers.git_importer import GitImporter
import pytest
import os
from app.tests.test_tools import clean_folder
import uuid
from app.models import add_job_to_db


@pytest.fixture
def prepared_tmp_git_folder():

    # Disable the connection with the db, since we are unittesting

    job_id = str(uuid.uuid4())
    temp_folder_path = "/tmp/gitimports/" + job_id
    test_git_repo = "https://github.com/rievo/icosphere"

    repo_contents = {
        "num_elements": 11,
        "project_name": "icosphere",
        "high_level_elements": 5,
    }

    # Add the job to the db
    add_job_to_db(
        {
            "import_service": "git",
            "import_token": "",
            "import_url": test_git_repo,
            "export_service": "",
            "export_token": "",
            "export_url": "",
        },
        job_id,
    )

    try:
        if not os.path.exists(temp_folder_path):
            print("Creating tmp folder")
            os.makedirs(temp_folder_path)

    except Exception as e:
        print(e)
        raise Exception("Error creating tmp folder")

    yield (job_id, temp_folder_path, test_git_repo, repo_contents)


def test_git_manifest_generation_fail(prepared_tmp_git_folder):

    (
        job_id,
        temp_folder_path,
        test_git_repo,
        repo_contents,
    ) = prepared_tmp_git_folder

    # Use a false url (the original reversed)
    params = {
        "import_url": test_git_repo[::-1],
        "import_token": "",
        "import_service": "git",
    }

    importer = GitImporter(job_id)

    manifest = importer.process_url(
        params["import_url"], params["import_token"]
    )

    clean_folder(temp_folder_path)

    assert manifest is None


def test_git_manifest_generation_success(prepared_tmp_git_folder):

    (
        job_id,
        temp_folder_path,
        test_git_repo,
        repo_contents,
    ) = prepared_tmp_git_folder

    params = {
        "import_url": test_git_repo,
        "import_token": "",
        "import_service": "git",
    }

    importer = GitImporter(job_id)

    manifest = importer.process_url(
        params["import_url"], params["import_token"]
    )

    clean_folder(temp_folder_path)

    assert manifest is not None
    assert (
        manifest.file_elements == repo_contents["num_elements"]
    )  # Hand-calculated
    assert manifest.project_name == repo_contents["project_name"]

    root_element = manifest.elements[0]

    assert root_element.id == "root"
    assert len(root_element.children) == repo_contents["high_level_elements"]
