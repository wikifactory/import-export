from .manifest_metadata import ManifestMetadata


class Manifest:

    def __init__(self):
        self.metatadata = ManifestMetadata()
        self.project_name = ""
        self.project_id = ""
        self.project_description = ""
        self.things = []
        pass
