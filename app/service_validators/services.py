import functools

from app.core.config import settings
from app.service_validators.base_validator import regex_validator

git_validator = functools.partial(
    regex_validator,
    service_id="git",
    regexes=[
        r"^https?:\/\/(www\.)?git(?P<service>hub|lab)\.com\/(?P<user>[\w-]+)/(?P<project>[\w-]+)"
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

dropbox_validator = functools.partial(
    regex_validator,
    service_id="dropbox",
    regexes=[
        r"^(https)?:\/\/(www\.)?dropbox\.com\/sh\/(?P<path>\w*\/\w*)\?dl=0$",
        r"^(https:\/\/)?(www\.)?dropbox\.com\/home\/(?P<path>[\S]+)$",
    ],
)

available_services = [
    git_validator,
    google_drive_validator,
    wikifactory_validator,
    dropbox_validator,
]
