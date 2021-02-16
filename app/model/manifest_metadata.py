from .user import User
from datetime import date
import json
from pydantic.dataclasses import dataclass
from dataclasses import field


@dataclass
class ManifestMetadata:

    date_created: str = field(init=False)
    last_date_updated: str = field(init=False)
    author: User = field(default_factory=lambda: User(name="unknown-author"))
    language: str = "EN"
    documentation_language: str = "EN"

    def __post_init__(self):
        current_date = date.today().strftime("%d/%m/%Y")

        self.date_created = current_date
        self.last_date_updated = current_date

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
