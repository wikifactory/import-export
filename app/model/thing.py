from .user import User


class Thing:

    def __init__(self):
        self.id = ""
        self.title = ""
        self.description = ""
        self.tags = []  # Similar to keywords

        # Required. This will be taken as the seed to be populated
        self.project_url = ""
        self.contact = User()
        self.contributors = []  # [User]

        self.associated_files_urls = []

        self.categories = []

        self.associated_standards = []  # [Standard]
