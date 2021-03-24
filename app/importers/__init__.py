from .dropbox import DropboxImporter
from .dropbox import validate_url as validate_dropbox
from .git import GitImporter
from .google_drive import GoogleDriveImporter

service_map = {
    "git": GitImporter,
    "google_drive": GoogleDriveImporter,
    "dropbox": DropboxImporter,
}
