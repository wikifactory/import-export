import os
from pathlib import Path

import dropbox

from app.model.element import Element, ElementType
from app.model.importer import Importer
from app.model.manifest import Manifest
from app.models import StatusEnum

temp_folder_path = "/tmp/dropboximports/"


class DropboxImporter(Importer):
    def __init__(self, job_id):

        self.job_id = job_id
        self.path = None
        self.elements_list = []
        self.dropbox_path_for_element = {}

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

        try:
            dropbox_handler = dropbox.Dropbox(auth_token)

            manifest = Manifest()

            self.process_folder_recursively(manifest, dropbox_handler, url)
            self.create_folder_structure_sync(self.elements_list)

            self.download_all_files(dropbox_handler, self.elements_list)

            # Finally, set the status
            self.set_status(StatusEnum.importing_successfully.value)

            return manifest
        except Exception as e:
            self.on_import_error_found(e)
            return None

    def process_folder_recursively(self, manifest, dropbox_handler, url):

        # From https://dropbox-sdk-python.readthedocs.io/en/latest/api/dropbox.html
        # ?highlight=list_folder#dropbox.dropbox.Dropbox.files_list_folder

        # Define an internal dict to store the elements:
        element_for_path = {}
        folders_paths_to_process = []

        folders_paths_to_process.append(url)

        # Create the root element
        root_element = Element()
        root_element.id = "root_element"
        root_element.name = url.split("/")[-1]
        root_element.type = ElementType.FOLDER
        root_element.path = self.path

        element_for_path[url] = root_element

        self.elements_list.append(root_element)

        # Start getting the content of the folder

        while len(folders_paths_to_process) > 0:

            # Get the next path to process, which will be a dropbox url
            next_path = folders_paths_to_process.pop(0)

            element = None

            # If this is the first time that I see that path,
            if next_path not in element_for_path:
                element = Element()
                element.id = next_path
                element.name = next_path.split("/")[-1]

                # From now on, this DB url will have an associated element
                element_for_path[next_path] = element

            else:
                # Otherwise, just return it
                element = element_for_path[next_path]

            try:
                # Get the content of the dropbox url

                entries = dropbox_handler.files_list_folder(next_path).entries

                # For each element inside that folder, check its type
                for entry in entries:

                    # If we are facing a file:
                    if isinstance(entry, dropbox.files.FileMetadata):

                        # Important: Increment the number of files to be processed
                        manifest.file_elements += 1

                        file_element = Element()
                        file_element.id = entry.id
                        file_element.type = ElementType.FILE
                        file_element.name = entry.name
                        file_element.path = element.path + "/" + file_element.name

                        element.children.append(file_element)

                        self.dropbox_path_for_element[file_element] = entry.path_lower

                        self.elements_list.append(file_element)

                    # otherwise, if we are facing a folder
                    elif isinstance(entry, dropbox.files.FolderMetadata):

                        # Create the manifest element for the folder

                        if entry.path_lower not in element_for_path:
                            folder_element = Element()
                            folder_element.type = ElementType.FOLDER
                            folder_element.id = entry.id
                            folder_element.name = entry.name
                            folder_element.path = (
                                element.path + "/" + folder_element.name
                            )

                            element.children.append(folder_element)

                            # Keep the reference
                            element_for_path[entry.path_lower] = folder_element

                            self.elements_list.append(folder_element)

                            # Finally, add the path to the folders_paths to be processed
                            folders_paths_to_process.append(entry.path_lower)

            except dropbox.exceptions.ApiError as err:
                print(
                    "Folder listing failed for",
                    next_path,
                    "-- assumed empty:",
                    err,
                )

        # Once done
        manifest.elements = [root_element]

    def create_folder_structure_sync(self, elements):
        for element in elements:
            if element.type == ElementType.FOLDER:
                # folder_path = os.path.dirname(element.path)
                try:
                    Path(element.path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(e)

    def download_all_files(self, dropbox_handler, elements):

        print("I will download {} elements".format(len(elements)))
        for i in range(len(elements)):
            ele = elements[i]

            print("Start downloading {}".format(ele.name))
            if ele.type == ElementType.FILE:

                self.download_file_from_element(dropbox_handler, ele)

    def download_file_from_element(self, dropbox_handler, element):

        # Get the dropbox path for that element
        db_path = self.dropbox_path_for_element[element]

        if db_path is not None:
            try:
                dropbox_handler.files_download_to_file(element.path, db_path)
            except Exception as e:
                print(e)
        else:
            raise "Dropbox path for element width id {} not found".format(element.id)
