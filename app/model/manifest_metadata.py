from .user import User


class ManifestMetadata:

    def __init__(self):
        self.date_created = ""
        self.last_date_updated = ""
        self.author = User()
        self.language = ""
        self.documentation_language = ""
