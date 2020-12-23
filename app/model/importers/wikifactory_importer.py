from ..importer import Importer
import os

from ..manifest import Manifest
from ..element import Element, ElementType


temp_folder_path = "/tmp/wikifactoryimports/"

files_for_project_query = """query q($space:String, $slug:String){
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

        except Exception as e:
            print(e)

    async def process_url(self, url, auth_token):
        print("WIKIFACTORY: Starting process")

        # url example: https://wikifactory.com/+growstack/nextfood-aeroponics-3b

        url_components = url.split("/")
        project_space = url_components[len(url_components) - 2]
        project_slug = url_components[len(url_components) - 1]

        # TODO: Use the space and slug to query the wikifactory server

        # TODO: Populate the manifest
        manifest = Manifest()

        return manifest

