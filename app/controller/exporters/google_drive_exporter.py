import os

from app.model.exporter import Exporter
from app.model.exporter import ExporterStatus, NotValidManifest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import httplib2
from oauth2client.client import AccessTokenCredentials
from mimetypes import MimeTypes
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveExporter(Exporter):
    def __init__(self, request_id):
        self.request_id = request_id
        self.set_status(ExporterStatus.INITIALIZED)

        self.manifest = None

        self.ids_for_elements = {}
        self.folder_id = ""

    def validate_url(url):
        raise NotImplementedError

    def export_manifest(self, manifest, export_url, export_token):

        print("GOOGLE DRIVE EXPORT STARTING....")

        self.manifest = manifest
        self.export_token = export_token

        self.folder_id = export_url.split("/")[-1]

        try:
            creds = AccessTokenCredentials(
                export_token, user_agent="https://www.googleapis.com/oauth2/v1/certs"
            )
            http = httplib2.Http()
            http = creds.authorize(http)
            self.drive_service = build(
                "drive", "v3", credentials=creds, cache_discovery=False
            )

        except Exception as e:
            print(e)

        # Check if we have a manifest
        if manifest is not None:

            self.project_path = manifest.elements[0].path

            manifest.iterate_through_elements(
                self, self.on_file_cb, self.on_folder_cb, self.on_finished_cb
            )
            return {"exported": "true", "manifest": manifest.toJson()}

        else:
            raise NotValidManifest()

    def on_file_cb(self, file_element):
        print("Uploading file {}".format(file_element.path))
        self.upload(file_element)

    def on_folder_cb(self, folder_element):
        if folder_element.id != "root":

            file_name = os.path.basename(folder_element.path)
            parent_path = folder_element.path.replace(file_name, "")
            parent_path = parent_path.rstrip("/")

            parent_id = self.ids_for_elements[parent_path]

            # Create the folder inside the target one
            folder_metadata = {
                "name": file_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = (
                self.drive_service.files()
                .create(body=folder_metadata, fields="id")
                .execute()
            )

            if folder_element.path not in self.ids_for_elements:
                self.ids_for_elements[folder_element.path] = folder.get("id")

        else:
            self.ids_for_elements[folder_element.path] = self.folder_id

            print(self.ids_for_elements)

    def on_finished_cb(self):
        print("FINISHED")

    def upload(self, element):
        mime = MimeTypes()

        parent_local_path = os.path.dirname(element.path)

        parent_id = self.ids_for_elements[parent_local_path]

        service = self.drive_service

        file_metadata = {"name": os.path.basename(element.path)}

        if parent_id:
            file_metadata["parents"] = [parent_id]

        media = MediaFileUpload(
            element.path,
            mimetype=mime.guess_type(os.path.basename(element.path))[0],
            resumable=True,
        )
        try:
            file = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
        except HttpError as e:
            print("HttpError uploading file")
            print(e)

        if element.path not in self.ids_for_elements:
            self.ids_for_elements[element.path] = file.get("id")
