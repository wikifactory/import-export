from app.model.constants import EXPORT_SERVICE, EXPORT_URL, EXPORT_TOKEN
from app.model.constants import WIKIFACTORY_SERVICE, GOOGLEDRIVE_SERVICE
from app.model.exporters.wikifactory_exporter import WikifactoryExporter
from app.model.exporters.google_drive_exporter import GoogleDriveExporter


class ExporterProxy:
    def __init__(self, request_id):
        self.request_id = request_id

    async def export_manifest(self, manifest, json_request):

        try:
            if json_request[EXPORT_SERVICE].lower() == WIKIFACTORY_SERVICE:
                return await self.handle_wikifactory(
                    manifest,
                    json_request[EXPORT_URL],
                    json_request[EXPORT_TOKEN],
                    self.request_id,
                )

            elif json_request[EXPORT_SERVICE].lower() == GOOGLEDRIVE_SERVICE:
                return await self.handle_google_drive(
                    manifest,
                    json_request[EXPORT_URL],
                    json_request[EXPORT_TOKEN],
                    self.request_id,
                )
        except Exception as e:
            print(e)

    async def handle_wikifactory(self, manifest, export_url, export_token, request_id):
        exporter = WikifactoryExporter(request_id)
        return await exporter.export_manifest(manifest, export_url, export_token)

    async def handle_google_drive(self, manifest, export_url, export_token, request_id):
        exporter = GoogleDriveExporter(request_id)
        return await exporter.export_manifest(manifest, export_url, export_token)
