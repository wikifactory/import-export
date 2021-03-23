from app.service_validators.base_validator import ServiceValidator


class GoogleDriveServiceValidator(ServiceValidator):
    def __init__(self) -> None:
        super.__init__(self)

        self.valid_regexes = [
            r"^https?:\/\/drive\.google\.com\/drive\/(u\/[0-9]+\/)?folders\/(?P<folder_id>[-\w]{25,})"
        ]
        self.service_id = "google_drive"
