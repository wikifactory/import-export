from app.model.exporter import Exporter

# from app.model.exporter import NotValidManifest
from app.models import StatusEnum


class GitExporter(Exporter):
    def __init__(self, job_id):
        self.job_id = job_id
        self.set_status(StatusEnum.exporting.value)

        self.manifest = None

        self.ids_for_elements = {}
        self.folder_id = ""

    def validate_url(url):
        raise NotImplementedError()

    def export_manifest(self, manifest, export_url, export_token):

        print("Git EXPORT STARTING....")

        self.manifest = manifest
        self.export_token = export_token

        raise NotImplementedError()
