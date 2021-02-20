import pytest
from app.routers.service_discover import discover_service_for_url_list


@pytest.mark.parametrize(
    "url, right_service",
    [
        ("https://www.dropbox.com/home/folder/otherfolder/file", "dropbox"),
        ("http://www.dropbox.com/home/anyfolder/anotherone", "dropbox"),
        (
            "https://drive.google.com/drive/u/0/folders/1-123456sYN8jsTeEpqrr5hSB0adKasdf",
            "googledrive",
        ),
        ("https://github.com/user/repo", "git"),
        ("ssh://git@github.com/<user>/<repository name>.git", "unknown"),
        ("ssh://git@github.com/user/repository_name.git", "git"),
        ("www.com", "unknown"),
        ("https://www.thingiverse.com/thing:1234567", "unknown"),
    ],
)
def test_service_discover(url, right_service):
    discovered_service = discover_service_for_url_list([url])
    assert right_service == discovered_service[url]
