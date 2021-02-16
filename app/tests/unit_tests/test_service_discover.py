from app.routers.service_discover import discover_service_for_url_list


def test_url_list():

    test_url_services = [
        {
            "url": "https://www.dropbox.com/home/folder/otherfolder/file",
            "service": "dropbox",
        },
        {
            "url": "http://www.dropbox.com/home/anyfolder/anotherone",
            "service": "dropbox",
        },
        {
            "url": "https://drive.google.com/drive/u/0/folders/1-123456sYN8jsTeEpqrr5hSB0adKasdf",
            "service": "googledrive",
        },
        {
            "url": "https://github.com/user/repo",
            "service": "git",
        },
        {
            "url": "ssh://git@github.com/<user>/<repository name>.git",
            "service": "unknown",
        },
        {
            "url": "ssh://git@github.com/user/repository_name.git",
            "service": "git",
        },
        {"url": "www.com", "service": "unknown"},
        {
            "url": "https://www.thingiverse.com/thing:1234567",
            "service": "unknown",
        },
    ]

    only_urls = []
    for r in test_url_services:
        only_urls.append(r["url"])

    discovered_service = discover_service_for_url_list(only_urls)

    for url in only_urls:

        right_service = [
            x["service"] for x in test_url_services if x["url"] == url
        ][0]

        assert right_service == discovered_service[url]
