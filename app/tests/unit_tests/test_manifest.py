from app.model.manifest import Manifest
from app.model.element import Element, ElementType

import pytest


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