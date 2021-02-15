from .user import User
from datetime import date
import json
from pydantic.dataclasses import dataclass


@dataclass
class ManifestMetadata:

    date_created: str = ""
    last_date_updated: str = ""
    author: User = User()
    language: str = ""
    documentation_language: str = ""

    def __init__(self, populate=True):
        if populate is True:
            self.default_populate()

    def default_populate(self):
        self.author.name = "unknown-author"
        self.language = "EN"
        self.documentation_language = "EN"

        current_date = date.today().strftime("%d/%m/%Y")

        self.date_created = current_date
        self.last_date_updated = current_date

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
