import io
import os
from app.model.importer import Importer
from app.model.manifest import Manifest
from app.model.element import Element, ElementType
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import httplib2
import oauth2client
from oauth2client.client import AccessTokenCredentials
from app.models import StatusEnum

from app.controller.importers.googledrive_errors import (
    CredentialsNotValid,
    DownloadError,
)

SCOPES = ["https://www.googleapis.com/auth/drive"]
query_c = "mimeType='application/vnd.google-apps.folder'"
query_fields = "nextPageToken, files(id,name, mimeType)"
query_idinparents = " in parents"


class GoogleDriveImporter(Importer):
    def __init__(self, job_id):

        self.job_id = job_id
        self.path = None

        self.elements_list = []

        self.temp_folder_path = "/tmp/gdimports/"

        self.make_sure_tmp_folder_is_created(self.temp_folder_path)

    def process_url(self, url, auth_token):

        print("Google Drive: Starting process")

        super().process_url(url, auth_token)

        creds = AccessTokenCredentials(
            auth_token,
            user_agent="https://www.googleapis.com/oauth2/v1/certs",
        )

        http = httplib2.Http()

        http = creds.authorize(http)

        drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

        # Create the manifest instance
        manifest = Manifest()

        # Start processing the folder
        # Here we will fill the manifest info with the googledrive files
        self.process_folder_recursively(manifest, drive_service, url)

        # Once we have the manifest, we create the folder structure
        self.create_folder_structure_sync(self.elements_list)

        # Next, download all the files to the associated folders
        self.download_all_files(drive_service, self.elements_list)

        # Finally, set the status
        self.set_status(StatusEnum.importing_successfully.value)

        return manifest

    def create_folder_structure_sync(self, elements):

        for element in elements:
            if element.type == ElementType.FOLDER:
                # folder_path = os.path.dirname(element.path)
                try:
                    Path(element.path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(e)

    def process_folder_recursively(self, manifest, drive_service, root_folder_id):

        # Init the folders array
        folders_ids = []
        element_for_id = {}

        # Append the initial folder id
        folders_ids.append(root_folder_id)

        root_element = Element(
            id=root_folder_id, path=self.path, type=ElementType.FOLDER
        )

        element_for_id[root_folder_id] = root_element

        self.elements_list.append(root_element)

        # While we have folders to process
        while len(folders_ids) > 0:

            next_id = folders_ids.pop(0)

            element = None

            # If this is the first time that I'm processing this item
            # (either folder or file)
            if next_id not in element_for_id:
                element = Element(id=next_id)
                element_for_id[next_id] = element
            else:
                element = element_for_id[next_id]

            # Perform a query and get all the files and subfolders given one
            (files, subfolders) = self.get_files_and_subfolders(drive_service, next_id)

            # For each subfolder
            for subfolder in subfolders:
                folders_ids.append(subfolder.get("id"))

                # Generate the appropiate element
                if subfolder.get("id") not in element_for_id:
                    f_ele = Element(
                        id=subfolder.get("id"),
                        name=subfolder.get("name"),
                        path=os.path.join(element.path, subfolder.get("name")),
                        type=ElementType.FOLDER,
                    )

                    element_for_id[f_ele.id] = f_ele

                    element.children.append(f_ele)

                    self.elements_list.append(f_ele)

            # For each file
            for f in files:

                # IMPORTANT: Increment the number of files for the manifest
                manifest.file_elements += 1

                ch_element = Element(
                    id=f.get("id"),
                    name=f.get("name"),
                    path=os.path.join(element.path, f.get("name")),
                    type=ElementType.FILE,
                )

                element.children.append(ch_element)

                self.elements_list.append(ch_element)

        # Finally, set the elements of the manifest
        manifest.elements = [root_element]

    def download_all_files(self, drive_service, elements):
        for i in range(len(elements)):
            ele = elements[i]
            if ele.type == ElementType.FILE:
                self.download_file_from_element(drive_service, ele)

    def get_files_and_subfolders(self, drive_service, folder_id):
        files = []
        subfolders = []
        last_page_token = None

        # Process the query
        while True:

            try:
                param = {
                    "q": "'" + folder_id + "'" + query_idinparents,
                    "fields": query_fields,
                }
                if last_page_token is not None:
                    param["pageToken"] = last_page_token

                response = drive_service.files().list(**param).execute()

                result_list = response["files"]

                for item in result_list:

                    if item.get("mimeType") == "application/vnd.google-apps.folder":
                        subfolders.append(item)
                    else:
                        files.append(item)

                page_token = response["nextPageToken"]

                if page_token == last_page_token or page_token is None:
                    break
                else:
                    last_page_token = page_token

            except (oauth2client.client.AccessTokenCredentialsError):
                self.on_import_error_found(None)
                raise CredentialsNotValid("")

        return (files, subfolders)

    def download_file_from_element(self, drive_service, element):

        request = drive_service.files().get_media(fileId=element.id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False

        if element.type == ElementType.FILE:
            try:
                while done is False:
                    status, done = downloader.next_chunk()
                    # print("{}".format(status.progress() * 100))

                print("File {} done".format(element.path))
                with open(element.path, "wb") as outfile:
                    outfile.write(fh.getbuffer())
            except (HttpError, httplib2.HttpLib2Error):
                raise DownloadError("")
