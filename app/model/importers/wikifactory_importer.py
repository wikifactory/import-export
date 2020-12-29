from ..importer import Importer
import os

from ..manifest import Manifest
from ..element import Element, ElementType
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import requests
import zipfile

temp_folder_path = "/tmp/wikifactoryimports/"
temp_zip_folder_path = "/tmp/wikifactoryzips/"

endpoint_url = "http://localweb:8080/api/graphql"
client_username = "dGVzdHVzZXIz"  # QUESTION: Where do I get this?


class WikifactoryImporterQuerys:

    repository_zip_query = gql(
        """
        query RepositoryZip($space: String, $slug: String) {
            project(space: $space, slug: $slug) {
            result {
                id
                slug
                contributionUpstream {
                id
                zipArchiveUrl
                }
            }
            userErrors {
                    message
                    key
                    code
            }
            }
        }
        """
    )

    files_for_project_query = gql(
        """query q($space:String, $slug:String){
            project(space:$space, slug:$slug){
                result{
                    id
                    contributions{
                        edges{
                            node{
                                id
                                title
                                files
                            }
                        }
                    }
                }
            }
        }"""
    )


class WikifactoryImporter(Importer):
    def __init__(self, request_id):

        # Assign this import process a unique id
        # This id will identify the tmp folder
        self.request_id = request_id

        self.path = None

        # Check if the tmp folder exists
        try:
            if not os.path.exists(temp_folder_path):
                print("Creating tmp folder")
                os.makedirs(temp_folder_path)

            self.path = temp_folder_path + self.request_id

            if not os.path.exists(temp_zip_folder_path):
                print("Creating tmp zip folder")
                os.makedirs(temp_zip_folder_path)

        except Exception as e:
            print(e)

    async def process_url(self, import_url, import_token):
        print("WIKIFACTORY: Starting process")

        manifest = Manifest()

        project_info = await self.get_project_details(import_url, import_token)

        # INFO: Maybe use the name or other field here?
        manifest.project_name = project_info["slug"]

        # Download the files
        await self.download_files_from_zip_url(project_info["zip_archive_url"])

        # Populate the manifest from the directory
        self.populate_manifest_from_folder_path(manifest, self.path)

        return manifest

    async def get_project_details(self, import_url, import_token):

        url_components = import_url.split("/")
        project_space = url_components[len(url_components) - 2]
        project_slug = url_components[len(url_components) - 1]

        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(import_token),
            },
        )

        async with Client(
            transport=transport, fetch_schema_from_transport=True
        ) as session:

            variables = {"space": project_space, "slug": project_slug}

            result = await session.execute(
                WikifactoryImporterQuerys.repository_zip_query,
                variable_values=variables,
            )

            if len(result["project"]["userErrors"]) > 0:

                for e in result["project"]["userErrors"]:
                    print(e)
                return None

            else:

                server_url = endpoint_url.replace("api/graphql", "")[:-1]
                project_id = result["project"]["result"]["id"]
                slug = result["project"]["result"]["slug"]

                zip_archive_url = (
                    server_url
                    + result["project"]["result"]["contributionUpstream"][
                        "zipArchiveUrl"
                    ]
                )

                return {
                    "project_id": project_id,
                    "zip_archive_url": zip_archive_url,
                    "slug": slug,
                }

    async def download_files_from_zip_url(self, zip_url):

        response = requests.get(zip_url)

        local_zip_path = temp_zip_folder_path + self.request_id

        # Write the zip file
        try:
            with open(local_zip_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            print(e)
            return

        # Now extract the zip file to the tmp folder and delete the zip

        try:
            # FIX: We are now unzipping to /tmp/wikifactoryimports/REQUEST_ID/SLUG
            with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
                zip_ref.extractall(self.path)

        except Exception as e:
            print(e)
            return

    def populate_manifest_from_folder_path(self, manifest, project_path):

        elements_dic = {}

        root_element = None

        for current_path, dirs_in_curr_path, files in os.walk(project_path):

            full_path = os.path.join(project_path, current_path)

            if full_path == project_path:
                # Root element
                root_element = Element()
                root_element.id = "root"
                root_element.path = full_path

                elements_dic[full_path] = root_element

            # Create the elements_dic entries for the folders
            for folder_name in dirs_in_curr_path:

                folder_element = Element()
                folder_element.type = ElementType.FOLDER

                current_folder_path = os.path.join(current_path, folder_name)

                folder_element.path = current_folder_path

                if full_path in elements_dic:
                    elements_dic[full_path].children.append(folder_element)
                    elements_dic[current_folder_path] = folder_element

            # For each children file
            for filename in files:

                # Create a child element
                file_element = Element()
                file_element.type = ElementType.FILE
                file_element.id = filename
                file_element.path = os.path.join(current_path, filename)

                if current_path in elements_dic:
                    elements_dic[current_path].children.append(file_element)

                # If we are at root level and the file is the readme, use it
                # for the description of the manifest
                if full_path == project_path and filename.lower() == "readme.md":
                    with open(file_element.path, "r") as file:
                        manifest.project_description = file.read()

        manifest.elements = [root_element]
