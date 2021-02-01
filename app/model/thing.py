import json


class Thing:
    def __init__(self):
        self.id = ""
        self.title = ""
        self.description = ""
        self.tags = []  # Similar to keywords

        # Required. This will be taken as the seed to be populated
        # self.thing_url = ""
        self.contact = None
        self.contributors = []  # [User]

        self.associated_files_urls = []

        self.categories = []

        self.associated_standards = []  # [Standard]

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
