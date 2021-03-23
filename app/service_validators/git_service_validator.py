from app.service_validators.base_validator import ServiceValidator


class GitServiceValidator(ServiceValidator):
    def __init__(self) -> None:
        super().__init__()

        self.valid_regexes = [
            r"^https?:\/\/(www\.)?git(hub|lab)\.com\/(?P<organization>[\w-]+)/(?P<project>[\w-]+)"
        ]
        self.service_id = "git"
