from .dropbox import DropboxImporter
from .dropbox import validate_url as validate_dropbox
from .git import GitImporter
from .git import validate_url as validate_git
from .google_drive import GoogleDriveImporter
from .google_drive import validate_url as validate_google_drive

service_map = {
    "git": GitImporter,
    "google_drive": GoogleDriveImporter,
    "dropbox": DropboxImporter,
}

# FIXME
validator_map = {
    "git": validate_git,
    "google_drive": validate_google_drive,
    "dropbox": validate_dropbox,
}
