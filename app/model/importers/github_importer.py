from ..importer import Importer
import os
from ..constants import GITHUB_ENV_VAR_NAME
from ..manifest import Manifest
from ..thing import Thing
from ..user import User


# from ..thing import Thing
from github import Github


class GithubAppTokenError(Exception):
    def __init__(self, message="Could not find the Github env var App token"):
        super().__init__(message)


class GithubImporter(Importer):
    def __init__(self, request_id):
        self.app_token = os.getenv(GITHUB_ENV_VAR_NAME)
        self.request_id = request_id
        self.github_access = None

        self.logged_user = User()

        if self.app_token is None:
            raise GithubAppTokenError()
        else:
            pass

    async def process_url(self, url, auth_token):
        print("GITHUB: Starting process of URL:")
        print(url)

        # Access to the github connector
        self.github_access = Github(self.app_token)

        # Parse the URL in order to get the name of the target repository

        # TODO: Validate the URL

        url_components = url.split("/")
        repository_owner = url_components[len(url_components) - 2]
        repository_name = url_components[len(url_components) - 1]

        repo_id = "{}/{}".format(repository_owner, repository_name)

        repo = self.github_access.get_repo(repo_id)

        manifest = Manifest()

        # self.populate_manifest_from_repository(manifest, repo)
        self.retrieve_commit_info(manifest, repo)

        return manifest.toJson()

    def retrieve_commit_info(self, manifest, repository):

        commit_list = repository.get_commits()
        for commit in commit_list:
            print(commit_list)
        pass

    def populate_manifest_from_repository(self, manifest, repository):

        print(repository)

        contents = repository.get_contents("")

        # Access recursively to all the files of the repository
        while contents:
            file_content = contents.pop(0)

            if file_content.type == "dir":
                contents.extend(repository.get_contents(file_content.path))
            else:
                if file_content.name == "README.md":

                    print("REAdME->")
                    print(file_content.url)
                    # print(file_content.content)
                    manifest.project_description = file_content.decoded_content.decode(
                        "utf-8"
                    ).replace('"', '\\"')
                else:
                    # Any other file will be inserted as a thing?
                    new_thing = Thing()
                    # new_thing.thing_url = file_content.url
                    new_thing.contact = self.logged_user
                    new_thing.title = file_content.name
                    new_thing.associated_files_urls.append(file_content.url)
                    manifest.things.append(new_thing)
                    pass

