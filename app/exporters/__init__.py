from .wikifactory import WikifactoryExporter
from .wikifactory import validate_url as validate_wikifactory

service_map = {
    "wikifactory": WikifactoryExporter,
}

# FIXME
validator_map = {"wikifactory": validate_wikifactory}
