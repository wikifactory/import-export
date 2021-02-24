import os
from re import search

import pygit2

from app.model.element import Element, ElementType
from app.model.importer import Importer
from app.model.manifest import Manifest
from app.models import StatusEnum

temp_folder_path = "/tmp/gitimports/"

ignored_folders = [".git"]


git_repo_regex = r"^(((git|ssh|http(s)?)|(git@[\w\.]+))(:(\/\/)?)([\w\.@\:\/\-~]+)(\.git)(\/)?)|(^http(s)?:\/\/github\.com(?:\/[^\s\/]+){2}$)"


class IgnoreCredentialsCallbacks(pygit2.RemoteCallbacks):
    def credentials(self, url, username_from_url, allowed_types):
        return None

    def certificate_check(self, certificate, valid, host):
        return True


class GitImporter(Importer):
    def __init__(self, job_id):

        # Assign this import process a unique id
        # This id will identify the tmp folder
        self.job_id = job_id

        self.temp_folder_path = "/tmp/gitimports/"

        self.make_sure_tmp_folder_is_created(self.temp_folder_path)

    def validate_url(url):
        return bool(search(git_repo_regex, url))

    def process_url(self, url, auth_token):
        print("GIT: Starting process")

        super().process_url(url, auth_token)

        try:
            # First, we clone the repo into the tmp folder
            pygit2.clone_repository(
                url, self.path, callbacks=IgnoreCredentialsCallbacks()
            )
            print("Repo cloned")

        except (pygit2.errors.GitError):
            self.on_import_error_found(None)
            return None

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

    def populate_manifest_from_repository_path(self, manifest, repo_path):
        elements_dic = {}

        root_element = None

        for current_path, dirs_in_curr_path, files in os.walk(repo_path):

            full_path = os.path.join(repo_path, current_path)

            if full_path == repo_path:

                # Root element
                root_element = Element(
                    id="root", path=full_path, type=ElementType.FOLDER
                )

                elements_dic[full_path] = root_element

            # Create the elements_dic entries for the folders
            for folder_name in dirs_in_curr_path:

                if folder_name not in ignored_folders:

                    current_folder_path = os.path.join(current_path, folder_name)
                    folder_element = Element(
                        type=ElementType.FOLDER, path=current_folder_path
                    )

                    if full_path in elements_dic:
                        elements_dic[full_path].children.append(folder_element)
                        elements_dic[current_folder_path] = folder_element

            # For each children file
            for filename in files:

                # Create a child element
                file_element = Element(
                    id=filename,
                    path=os.path.join(current_path, filename),
                    type=ElementType.FILE,
                )

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
