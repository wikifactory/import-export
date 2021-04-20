from .dropbox import DropboxImporter
from .git import GitImporter
from .google_drive import GoogleDriveImporter
from .wikifactory import WikifactoryImporter

service_map = {
    "git": GitImporter,
    "google_drive": GoogleDriveImporter,
    "dropbox": DropboxImporter,
    "wikifactory": WikifactoryImporter,
}
