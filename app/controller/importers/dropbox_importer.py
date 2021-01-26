import os
from app.model.importer import Importer
from app.model.manifest import Manifest


temp_folder_path = "/tmp/dropboximports/"


class DropboxImporter(Importer):
    def __init__(self, job_id):

        self.job_id = job_id
        self.path = None

        # Check if the tmp folder exists
        try:
            if not os.path.exists(temp_folder_path):
                print("Creating tmp folder")
                os.makedirs(temp_folder_path)

            self.path = temp_folder_path + self.job_id

        except Exception as e:
            print(e)

    def process_url(self, url, auth_token):

        print("Dropbox: Starting process of URL: {}".format(url))
        # Create the manifest instance
        manifest = Manifest()
        return manifest
