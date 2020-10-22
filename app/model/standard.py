# from certification import Certification
import json


class Standard:
    def __init__(self):
        self.id = ""
        self.title = ""
        self.reference = ""
        self.certifications = []  # [Certification]
    
    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
