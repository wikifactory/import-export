import functools

from app.core.config import settings
from app.service_validators.base_validator import regex_validator

git_validator = functools.partial(
    regex_validator,
    service_id="git",
    regexes=[
        r"^https?:\/\/(www\.)?git(hub|lab)\.com\/(?P<organization>[\w-]+)/(?P<project>[\w-]+)"
    ],
)


google_drive_validator = functools.partial(
    regex_validator,
    service_id="google_drive",
    regexes=[
        r"^https?:\/\/drive\.google\.com\/drive\/(u\/[0-9]+\/)?folders\/(?P<folder_id>[-\w]{25,})"
    ],
)


wikifactory_validator = functools.partial(
    regex_validator,
    service_id="wikifactory",
    regexes=[
        fr"^(?:http(s)?:\/\/)?(www\.)?{settings.WIKIFACTORY_API_HOST}\/(?P<space>[@+][\w-]+)\/(?P<slug>[\w-]+)$"
    ],
)

available_services = [git_validator, google_drive_validator, wikifactory_validator]
