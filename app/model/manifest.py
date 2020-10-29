from .manifest_metadata import ManifestMetadata
import json


class Manifest:

    def __init__(self):
        self.metatadata = ManifestMetadata()
        self.project_name = ""
        self.project_id = ""
        self.project_description = ""
        self.elements = []
        self.collaborators = []
        pass

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
