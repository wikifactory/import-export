from .git import GitImporter
from .google_drive import GoogleDriveImporter

service_map = {
    "git": GitImporter,
    "google_drive": GoogleDriveImporter,
}
