from ..importer import Importer
from ..manifest import Manifest
from ..element import Element, ElementType

from ...credentials import CLIENT_ID, CLIENT_SECRET

from googleapiclient.discovery import build
import httplib2
from oauth2client.client import AccessTokenCredentials

SCOPES = ["https://www.googleapis.com/auth/drive"]
query_c = "mimeType='application/vnd.google-apps.folder'"
query_fields = "nextPageToken, files(id,name, mimeType)"
query_idinparents = " in parents"


class GoogleDriveImporter(Importer):
    def __init__(self):
        pass

    async def process_url(self, url, auth_token):

        print("Google Drive: Starting process of folder:")
        print(url)

        try:
            creds = AccessTokenCredentials(
                auth_token, user_agent="https://www.googleapis.com/oauth2/v1/certs"
            )
            http = httplib2.Http()
            http = creds.authorize(http)
            drive_service = build("drive", "v3", credentials=creds)

        except Exception as e:
            print(e)

        # Create the manifest instance
        manifest = Manifest()

        self.process_folder_recursively(manifest, drive_service, url)

        return manifest.toJson()

    def process_folder_recursively(self, manifest, drive_service, root_folder_id):

        # Init the folders array
        folders_ids = []
        element_for_id = {}

        # Append the initial folder id
        folders_ids.append(root_folder_id)

        root_element = Element()
        root_element.id = root_folder_id
        root_element.type = ElementType.FOLDER
        element_for_id[root_folder_id] = root_element

        # While we have folders to process
        while len(folders_ids) > 0:

            next_id = folders_ids.pop(0)

            element = None

            # If this is the first time that I'm processing this item
            # (either folder or file)
            if next_id not in element_for_id:
                element = Element()
                element.id = next_id
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
                    f_ele = Element()
                    f_ele.type = ElementType.FOLDER
                    f_ele.id = subfolder.get("id")
                    f_ele.name = subfolder.get("name")
                    element_for_id[f_ele.id] = f_ele

                    element.children.append(f_ele)

            # For each file
            for f in files:

                # Create the element

                ch_element = Element()
                ch_element.id = f.get("id")
                ch_element.path = f.get("name")
                ch_element.type = ElementType.FILE

                element.children.append(ch_element)

        # Finally, set the elements of the manifest
        manifest.elements = [root_element]

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

            except Exception as e:
                print(e)
                break

        return (files, subfolders)
