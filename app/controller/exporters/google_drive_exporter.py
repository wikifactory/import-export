from app.model.exporter import Exporter
from app.model.exporter import ExporterStatus, NotValidManifest


class GoogleDriveExporter(Exporter):
    def __init__(self, request_id):
        self.request_id = request_id
        self.set_status(ExporterStatus.INITIALIZED)

        self.manifest = None

    def validate_url(url):
        raise NotImplementedError

    def export_manifest(self, manifest, export_url, export_token):

        # https://drive.google.com/drive/folders/1fWEQbbCC4jwpF-lDBuJIAUWDT4LUbUDr?usp=sharing
        self.manifest = manifest

        folder_id = export_url.split("/")[-1]
