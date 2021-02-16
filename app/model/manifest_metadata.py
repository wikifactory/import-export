from .user import User
from datetime import date
import json
from pydantic.dataclasses import dataclass
from dataclasses import field


@dataclass
class ManifestMetadata:

    date_created: str = ""
    last_date_updated: str = ""
    author: User = field(default_factory=User)
    language: str = ""
    documentation_language: str = ""

    @classmethod
    def default(cls) -> "ManifestMetadata":
        metadata = cls()

        metadata.author.name = "unknown-author"
        metadata.language = "EN"
        metadata.documentation_language = "EN"

        current_date = date.today().strftime("%d/%m/%Y")

        metadata.date_created = current_date
        metadata.last_date_updated = current_date

        return metadata

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
