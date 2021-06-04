from .dropbox import DropboxExporter
from .git import GitExporter
from .wikifactory import WikifactoryExporter

service_map = {
    "wikifactory": WikifactoryExporter,
    "dropbox": DropboxExporter,
    "git": GitExporter,
}
