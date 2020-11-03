from ..importer import Importer
from ..manifest import Manifest
from ..element import Element, ElementType

from ...credentials import CLIENT_ID, CLIENT_SECRET

from googleapiclient.discovery import build
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive']


query_c = "mimeType='application/vnd.google-apps.folder'"
fields_c = "nextPageToken, files(id,name, mimeType)"
query_infolder = " in parents"


class GoogleDriveImporter(Importer):

    def __init__(self):
        pass

    async def process_url(self, url, auth_token):

        # Create the credentials object
        creds = self.get_credentials_object(auth_token)

        try:
            # Create the connection with the google drive service
            drive_service = build('drive', 'v3', creds)

            print(drive_service)

            self.list_contents_of_folder_with_id(drive_service, url)

        except Exception as e:
            print(e)

        # Create the manifest instance
        manifest = Manifest()

        return manifest.toJson()

    def list_contents_of_folder_with_id(drive_service, folder_id):
        list_result = []
        last_page_token = None

        # Process the query
        while True:

            try:
                param = {"q": "'" + folder_id + "'" + query_infolder,
                         "fields": fields_c}
                if last_page_token is not None:
                    param['pageToken'] = last_page_token

                response = drive_service.files().list(**param).execute()

                list_result.extend(response['files'])

                page_token = response['nextPageToken']

                if page_token == last_page_token or page_token is None:
                    break
                else:
                    last_page_token = page_token

            except Exception as e:
                print(e)
                break

        for file in list_result:
            
            print('Found file: {} ({}) {}'.format(file.get('name'),
                                                  file.get('id'),
                                                  file.get('mimeType')))

        print("total folders: {}".format(len(list_result)))

    def get_credentials_object(self, token):

        cred = {}
        cred["token"] = token
        cred["_id_token"] = None
        cred["_scopes"] = SCOPES
        cred["_token_uri"] = "https://oauth2.googleapis.com/token"
        cred["_client_id"] = CLIENT_ID
        cred["_client_secret"] = CLIENT_SECRET
        cred["_quota_project_id"] = None

        return cred
