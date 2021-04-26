from .git import GitExporter
from .wikifactory import WikifactoryExporter

service_map = {"wikifactory": WikifactoryExporter, "git": GitExporter}
