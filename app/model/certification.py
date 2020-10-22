import json


class Certification:
    def __init__(self):
        self.certifier_id = ""
        self.data_awarded = ""
        self.url = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
