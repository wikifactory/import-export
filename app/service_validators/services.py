from app.service_validators.git_service_validator import GitServiceValidator
from app.service_validators.googledrive_service_validator import (
    GoogleDriveServiceValidator,
)
from app.service_validators.wikifactory_service_validator import (
    WikifactoryServiceValidator,
)

available_services = [
    GitServiceValidator(),
    GoogleDriveServiceValidator(),
    WikifactoryServiceValidator(),
]
