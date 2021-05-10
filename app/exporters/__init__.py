from .dropbox import DropboxExporter
from .wikifactory import WikifactoryExporter

service_map = {"wikifactory": WikifactoryExporter, "dropbox": DropboxExporter}
