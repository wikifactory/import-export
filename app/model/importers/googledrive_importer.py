from ..importer import Importer
from ..manifest import Manifest
from ..element import Element, ElementType

from ...credentials import CLIENT_ID, CLIENT_SECRET

from googleapiclient.discovery import build
import httplib2
from oauth2client.client import AccessTokenCredentials

SCOPES = ['https://www.googleapis.com/auth/drive']
query_c = "mimeType='application/vnd.google-apps.folder'"
fields_c = "nextPageToken, files(id,name, mimeType)"
query_infolder = " in parents"


class GoogleDriveImporter(Importer):

    def __init__(self):
        pass

    async def process_url(self, url, auth_token):

        print("Google Drive: Starting process of folder:")
        print(url)

        try:
            creds = AccessTokenCredentials(auth_token, user_agent="https://www.googleapis.com/oauth2/v1/certs")
            http = httplib2.Http()
            http = creds.authorize(http)
            drive_service = build('drive', 'v3', credentials=creds)
            self.list_contents_of_folder_with_id(drive_service, url)

        except Exception as e:
            print(e)

        # Create the manifest instance
        manifest = Manifest()

        return manifest.toJson()

    def list_contents_of_folder_with_id(self, drive_service, folder_id):
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
        cred["installed"] = {}
        cred["installed"]["token"] = token
        cred["installed"]["project_id"] = "gdtest-293711"
        cred["installed"]["id_token"] = None
        cred["installed"]["scopes"] = SCOPES
        cred["installed"]["token_uri"] = "https://oauth2.googleapis.com/token"
        cred["installed"]["client_id"] = CLIENT_ID
        cred["installed"]["client_secret"] = CLIENT_SECRET
        cred["installed"]["auth_provider_x509_cert_url"] = "https://www.googleapis.com/oauth2/v1/certs"
        cred["installed"]["quota_project_id"] = None

        return cred
