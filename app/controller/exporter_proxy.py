from app.model.constants import EXPORT_SERVICE, EXPORT_URL, EXPORT_TOKEN
from app.model.constants import WIKIFACTORY_SERVICE, GOOGLEDRIVE_SERVICE
from app.controller.exporters.wikifactory_exporter import WikifactoryExporter
from app.controller.exporters.google_drive_exporter import GoogleDriveExporter


class ExporterProxy:
    def __init__(self, job_id):
        self.job_id = job_id

    def export_manifest(self, manifest, json_request):

        try:
            if json_request[EXPORT_SERVICE].lower() == WIKIFACTORY_SERVICE:
                return self.handle_wikifactory(
                    manifest,
                    json_request[EXPORT_URL],
                    json_request[EXPORT_TOKEN],
                    self.job_id,
                )

            elif json_request[EXPORT_SERVICE].lower() == GOOGLEDRIVE_SERVICE:
                return self.handle_google_drive(
                    manifest,
                    json_request[EXPORT_URL],
                    json_request[EXPORT_TOKEN],
                    self.job_id,
                )
        except Exception as e:
            print(e)

    def handle_wikifactory(self, manifest, export_url, export_token, job_id):
        exporter = WikifactoryExporter(job_id)
        return exporter.export_manifest(manifest, export_url, export_token)

    def handle_google_drive(self, manifest, export_url, export_token, job_id):
        exporter = GoogleDriveExporter(job_id)
        return exporter.export_manifest(manifest, export_url, export_token)
