from ..importer import Importer
import os
import git
import time
from ..manifest import Manifest
from ..element import Element, ElementType
import tempfile

temp_folder_path = "/tmp/gitimports/"


class Progress(git.remote.RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print('update({}, {}, {}, {})'.format(op_code, 
                                              cur_count, max_count, message))


class GitImporter(Importer):

    def __init__(self):

        # Assign this import process a unique id
        # This id will identify the tmp folder
        self.id = str(int(round(time.time() * 1000)))

        self.path = None

        # Check if the tmp folder exists
        try:
            if not os.path.exists(temp_folder_path):
                print("Creating tmp folder")
                os.makedirs(temp_folder_path)

            self.path = temp_folder_path + self.id

        except Exception as e:
            print(e)

    async def process_url(self, url, auth_token):
        print("GIT: Starting process")

        # TODO: Check if the repo url is valid

        # TODO: Check if the repo is local?

        # If the url / path is valid, start the process
        # First, we clone the repo into the tmp folder
        repo = git.Repo.clone_from(url, self.path, progress=Progress())
        manifest = Manifest()

        self.populate_manifest_from_repository_path(manifest,
                                                    self.path)

        self.fill_contributors(manifest, repo)

        return manifest.toJson()

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

            if(full_path == repo_path):
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

                elements_dic[full_path].children.append(folder_element)
                elements_dic[current_folder_path] = folder_element

            # For each children file
            for filename in files:

                # Create a child element
                file_element = Element()
                file_element.type = ElementType.FILE
                file_element.id = filename
                file_element.path = os.path.join(current_path, filename)

                elements_dic[current_path].children.append(file_element)

        manifest.elements = [root_element]
