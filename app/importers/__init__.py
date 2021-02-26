from .git import GitImporter
from .git import validate_url as validate_git
from .google_drive import GoogleDriveImporter
from .google_drive import validate_url as validate_google_drive

service_map = {
    "git": GitImporter,
    "google_drive": GoogleDriveImporter,
}

# FIXME
validator_map = {"git": validate_git, "google_drive": validate_google_drive}
