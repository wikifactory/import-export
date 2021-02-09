from app.model.importer import Importer
import os
import pygit2

from app.model.manifest import Manifest
from app.model.element import Element, ElementType
from app.models import StatusEnum

temp_folder_path = "/tmp/gitimports/"

ignored_folders = [".git"]


class IgnoreCredentialsCallbacks(pygit2.RemoteCallbacks):
    def __init__(self, credentials=None, certificate=None):
        super(self.__class__, self).__init__(credentials, certificate)

    def credentials(self):
        return ""


class GitImporter(Importer):
    def __init__(self, job_id):

        # Assign this import process a unique id
        # This id will identify the tmp folder
        self.job_id = job_id

        self.path = None

        self.set_status(StatusEnum.importing.value)

        # Check if the tmp folder exists
        try:
            if not os.path.exists(temp_folder_path):
                print("Creating tmp folder")
                os.makedirs(temp_folder_path)

            self.path = temp_folder_path + self.job_id

        except Exception as e:
            print(e)
            self.set_status(StatusEnum.importing_error_data_unreachable.value)

    def validate_url():
        pass

    def process_url(self, url, auth_token):
        print("GIT: Starting process")
        # TODO: Check if the repo url is valid

        # TODO: Check if the repo is local?

        # If the url / path is valid, start the process
        # First, we clone the repo into the tmp folder

        try:

            pygit2.clone_repository(
                url, self.path, callbacks=IgnoreCredentialsCallbacks()
            )
            print("Repo cloned")

            # Create the manifest instance
            manifest = Manifest()

            # Fill some basic information of the project
            manifest.project_name = os.path.basename(os.path.normpath(url))
            manifest.source_url = url

            # Populate the manifest from the directory
            self.populate_manifest_from_repository_path(manifest, self.path)

            # Finally, set the status
            self.set_status(StatusEnum.importing_successfully.value)
            return manifest

        except Exception as e:
            self.set_status(StatusEnum.importing_error_data_unreachable.value)
            print(e)
            return None

    def fill_contributors(self, manifest, repo):
        branch = repo.active_branch

        # Extract a list of commits to retrieve the emails
        email_list = []
        commits = list(repo.iter_commits(branch.name))
        for c in commits:
            if c.author.email not in email_list:
                email_list.append(c.author.email)

        manifest.collaborators = email_list

    def populate_manifest_from_repository_path(self, manifest, repo_path):
        elements_dic = {}

        root_element = None

        for current_path, dirs_in_curr_path, files in os.walk(repo_path):

            full_path = os.path.join(repo_path, current_path)

            if full_path == repo_path:
                # Root element
                root_element = Element()
                root_element.id = "root"
                root_element.path = full_path
                root_element.type = ElementType.FOLDER

                elements_dic[full_path] = root_element

            # Create the elements_dic entries for the folders
            for folder_name in dirs_in_curr_path:

                if folder_name not in ignored_folders:
                    folder_element = Element()
                    folder_element.type = ElementType.FOLDER

                    current_folder_path = os.path.join(
                        current_path, folder_name
                    )

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

                    # IMPORTANT: Increment the number of files for the manifest
                    manifest.file_elements += 1

                # If we are at root level and the file is the readme, use it
                # for the description of the manifest
                if full_path == repo_path and filename.lower() == "readme.md":
                    with open(file_element.path, "r") as file:
                        manifest.project_description = file.read()

        manifest.elements = [root_element]
