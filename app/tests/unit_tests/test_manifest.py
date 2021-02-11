from app.model.manifest import Manifest
from app.model.element import Element, ElementType
from app.models import add_job_to_db
from app.controller.importers.git_importer import (
    GitImporter,
)
from app.tests.integration_tests.test_job import create_job
import pytest
import os


@pytest.fixture()
def get_plain_manifest():

    manifest = Manifest()
    manifest.project_name = "test_project"
    manifest.project_id = "test_id"
    manifest.project_description = "A manifest for testing"
    manifest.source_url = "http://testurl.com"

    ele1 = Element()
    ele1.type = ElementType.FILE
    ele1.id = "ele1"
    ele1.path = "/ele1"

    ele2 = Element()
    ele2.type = ElementType.FILE
    ele2.id = "ele2"
    ele2.path = "/ele2"

    manifest.elements.append(ele1)
    manifest.elements.append(ele2)

    yield manifest


def test_manifest_empty_creation():

    manifest = Manifest()

    assert manifest.file_elements == 0
    assert len(manifest.elements) == 0
    assert manifest.project_id == ""
    assert manifest.project_description == ""
    assert len(manifest.elements) == 0
    assert manifest.source_url == ""


def test_plain_manifest(get_plain_manifest):

    manifest = get_plain_manifest

    assert len(manifest.elements) == 2


def project_folder_generator(path):

    folder_structure = [
        ("{}".format(path), ["folderA", "folderB"], ["file3.txt"]),
        ("{}/folderA".format(path), [], []),
        ("{}/folderB".format(path), [], ["file1.png", "file2.csv"]),
    ]

    for row in folder_structure:
        yield row


def os_path_exits(path):
    return True


def test_mocked_folder_git(monkeypatch):

    test_folder_name = "/testfolder"
    monkeypatch.setattr(
        os.path,
        "exists",
        os_path_exits,
    )

    monkeypatch.setattr(
        os,
        "walk",
        project_folder_generator,
    )

    # Add the job to the DB
    (job_id, job) = create_job()
    add_job_to_db(job, job_id)

    importer = GitImporter(job_id)

    temp_manifest = Manifest()

    importer.populate_manifest_from_repository_path(
        temp_manifest, test_folder_name
    )

    root_element = temp_manifest.elements[0]

    assert root_element.id == "root"
    assert root_element.type == "2"

    first_level_childrens = root_element.children

    assert len(first_level_childrens) == 3  # folderA, folderB, file3

    # Check the childrens of folderA
    for el in first_level_childrens:
        if el.path == "{}/folderA".format(test_folder_name):
            assert len(el.children) == 0
            assert el.type == "2"  # Of type folder
            break

    # Check the childrens of folderB
    for el in first_level_childrens:
        if el.path == "{}/folderB".format(test_folder_name):
            assert len(el.children) == 2
            assert el.type == "2"  # Of type folder
            break
