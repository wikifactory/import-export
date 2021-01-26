from .user import User
from datetime import date
import json


class ManifestMetadata:
    def __init__(self, populate=True):
        self.date_created = ""
        self.last_date_updated = ""
        self.author = User()
        self.language = ""
        self.documentation_language = ""

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
