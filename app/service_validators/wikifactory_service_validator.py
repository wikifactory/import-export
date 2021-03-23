from app.core.config import settings
from app.service_validators.base_validator import ServiceValidator


class WikifactoryServiceValidator(ServiceValidator):
    def __init__(self) -> None:
        super.__init__(self)

        self.valid_regexes = [
            fr"^(?:http(s)?:\/\/)?(www\.)?{settings.WIKIFACTORY_API_HOST}\/(?P<space>[@+][\w-]+)\/(?P<slug>[\w-]+)$"
        ]
        self.service_id = "wikifactory"
