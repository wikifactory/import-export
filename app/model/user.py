import json


class User:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.affiliation = ""
        self.email = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
