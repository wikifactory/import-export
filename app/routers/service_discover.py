from app.controller.importers.dropbox_importer import DropboxImporter
from app.controller.importers.git_importer import GitImporter
from app.controller.importers.googledrive_importer import GoogleDriveImporter
from app.controller.importers.wikifactory_importer import WikifactoryImporter


def discover_service_for_url_list(urls):
    result = {}

    for url in urls:

        if GitImporter.validate_url(url) is True:
            result[url] = "git"
        elif DropboxImporter.validate_url(url) is True:
            result[url] = "dropbox"
        elif GoogleDriveImporter.validate_url(url) is True:
            result[url] = "googledrive"
        elif WikifactoryImporter.validate_url(url) is True:
            result[url] = "wikifactory"
        else:
            result[url] = "unknown"

    return result
