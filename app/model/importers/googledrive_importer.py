import time
import os
import io
import asyncio
from ..importer import Importer
from ..manifest import Manifest
from ..element import Element, ElementType
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import httplib2
from oauth2client.client import AccessTokenCredentials

import aiohttp
from socket import AF_INET


temp_folder_path = "/tmp/gdimports/"
SIZE_POOL_AIOHTTP = 100

SCOPES = ["https://www.googleapis.com/auth/drive"]
query_c = "mimeType='application/vnd.google-apps.folder'"
query_fields = "nextPageToken, files(id,name, mimeType)"
query_idinparents = " in parents"


class SingletonAiohttp:
    sem: asyncio.Semaphore = None
    aiohttp_client: aiohttp.ClientSession = None

    @classmethod
    def get_aiohttp_client(cls) -> aiohttp.ClientSession:
        if cls.aiohttp_client is None:
            timeout = aiohttp.ClientTimeout(total=2)
            connector = aiohttp.TCPConnector(
                family=AF_INET, limit_per_host=SIZE_POOL_AIOHTTP
            )
            cls.aiohttp_client = aiohttp.ClientSession(
                timeout=timeout, connector=connector
            )

        return cls.aiohttp_client

    @classmethod
    async def close_aiohttp_client(cls):
        if cls.aiohttp_client:
            await cls.aiohttp_client.close()
            cls.aiohttp_client = None

    @classmethod
    async def query_url(cls, url: str):
        client = cls.get_aiohttp_client()

        try:
            async with client.post(url) as response:
                if response.status != 200:
                    return {"ERROR OCCURED" + str(await response.text())}

                json_result = await response.json()
        except Exception as e:
            return {"ERROR": e}

        return json_result


class GoogleDriveImporter(Importer):
    def __init__(self, request_id):

        self.request_id = request_id
        self.path = None

        self.elements_list = []

        # Check if the tmp folder exists
        try:
            if not os.path.exists(temp_folder_path):
                print("Creating tmp folder")
                os.makedirs(temp_folder_path)

            self.path = temp_folder_path + self.request_id

        except Exception as e:
            print(e)

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
        self.create_folder_structure_sync(self.elements_list)

        await self.download_all_files(drive_service, self.elements_list)

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

        root_element = Element()
        root_element.id = root_folder_id
        root_element.type = ElementType.FOLDER
        root_element.path = self.path
        element_for_id[root_folder_id] = root_element

        self.elements_list.append(root_element)

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
                    f_ele.path = element.path + "/" + f_ele.name
                    element_for_id[f_ele.id] = f_ele

                    element.children.append(f_ele)

                    self.elements_list.append(f_ele)

            # For each file
            for f in files:

                # Create the element

                ch_element = Element()
                ch_element.id = f.get("id")
                ch_element.path = element.path + "/" + f.get("name")
                ch_element.type = ElementType.FILE

                element.children.append(ch_element)

                self.elements_list.append(ch_element)

        # Finally, set the elements of the manifest
        manifest.elements = [root_element]

    async def download_all_files(self, drive_service, elements):

        async_calls = []

        for i in range(len(elements)):
            ele = elements[i]
            if ele.type == ElementType.FILE:
                async_calls.append(self.download_file_from_element(drive_service, ele))

        all_results = await asyncio.gather(*async_calls)
        return all_results

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

    async def download_file_from_element(self, drive_service, element):

        request = drive_service.files().get_media(fileId=element.id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False

        if element.type == ElementType.FILE:
            try:
                while done is False:
                    status, done = downloader.next_chunk()
                    # print("{}".format(status.progress() * 100))
            except Exception as e:
                print(e)

            try:
                print("File {} done".format(element.path))
                with open(element.path, "wb") as outfile:
                    outfile.write(fh.getbuffer())
            except Exception as e:
                print(e)