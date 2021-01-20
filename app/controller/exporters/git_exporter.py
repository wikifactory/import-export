from app.model.exporter import Exporter
from app.model.exporter import ExporterStatus, NotValidManifest


class GitExporter(Exporter):
    def __init__(self, job_id):
        self.job_id = job_id
        self.set_status(ExporterStatus.INITIALIZED)

        self.manifest = None

        self.ids_for_elements = {}
        self.folder_id = ""

    def validate_url(url):
        raise NotImplementedError

    def export_manifest(self, manifest, export_url, export_token):

        print("Git EXPORT STARTING....")

        self.manifest = manifest
        self.export_token = export_token

        raise NotImplementedError

