from ..model.constants import THINGIVERSE_SERVICE, MYMINIFACTORY_SERVICE
from ..model.constants import GITHUB_SERVICE, GIT_SERVICE
from ..model.constants import SOURCE_URL, AUTH_TOKEN, SERVICE
from ..model.constants import GOOGLEDRIVE_SERVICE
from ..model.importers.thingiverse_importer import ThingiverseImporter
from ..model.importers.github_importer import GithubImporter
from ..model.importers.git_importer import GitImporter
from ..model.importers.googledrive_importer import GoogleDriveImporter
from ..model.importers.myminifactory_importer import MyMiniFactoryImporter

import time


class ImporterProxy:
    def __init__(self, request_id):
        self.request_id = request_id

    async def handle_request(self, json_request):

        if json_request[SERVICE].lower() == THINGIVERSE_SERVICE:

            return await self.handle_thingiverse(
                json_request[SOURCE_URL], json_request[AUTH_TOKEN], self.request_id
            )

        elif json_request[SERVICE].lower() == GITHUB_SERVICE:
            return await self.handle_github(
                json_request[SOURCE_URL], json_request[AUTH_TOKEN], self.request_id
            )

        elif json_request[SERVICE].lower() == GIT_SERVICE:
            return await self.handle_git(
                json_request[SOURCE_URL], json_request[AUTH_TOKEN], self.request_id
            )

        elif json_request[SERVICE].lower() == MYMINIFACTORY_SERVICE:
            return await self.handle_myminifactory(
                json_request[SOURCE_URL], json_request[AUTH_TOKEN], self.request_id
            )

        elif json_request[SERVICE].lower() == GOOGLEDRIVE_SERVICE:
            return await self.handle_googledrive(
                json_request[SOURCE_URL], json_request[AUTH_TOKEN], self.request_id
            )
        else:
            raise NotImplementedError()

    async def handle_thingiverse(self, url, auth_token, request_id):
        imp = ThingiverseImporter(request_id)
        return await imp.process_url(url, auth_token)

    async def handle_github(self, url, auth_token, request_id):
        imp = GithubImporter(request_id)
        return await imp.process_url(url, auth_token)

    async def handle_git(self, url, auth_token, request_id):
        imp = GitImporter(request_id)
        return await imp.process_url(url, auth_token)

    async def handle_googledrive(self, url, auth_token, request_id):
        imp = GoogleDriveImporter(request_id)
        return await imp.process_url(url, auth_token)

    async def handle_myminifactory(self, url, auth_token, request_id):
        imp = MyMiniFactoryImporter(request_id)
        return await imp.process_url(url, auth_token)
