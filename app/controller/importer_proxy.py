from app.model.constants import (
    THINGIVERSE_SERVICE,
    MYMINIFACTORY_SERVICE,
    WIKIFACTORY_SERVICE,
)
from app.model.constants import IMPORT_SERVICE, IMPORT_URL, IMPORT_TOKEN
from app.model.constants import GITHUB_SERVICE, GIT_SERVICE

from app.model.constants import GOOGLEDRIVE_SERVICE
from app.controller.importers.thingiverse_importer import ThingiverseImporter
from app.controller.importers.git_importer import GitImporter
from app.controller.importers.googledrive_importer import GoogleDriveImporter
from app.controller.importers.myminifactory_importer import MyMiniFactoryImporter
from app.controller.importers.wikifactory_importer import WikifactoryImporter


class ImporterProxy:
    def __init__(self, request_id):
        self.request_id = request_id

    async def handle_request(self, json_request):

        if json_request[IMPORT_SERVICE].lower() == THINGIVERSE_SERVICE:

            return await self.handle_thingiverse(
                json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.request_id
            )

        elif json_request[IMPORT_SERVICE].lower() == GIT_SERVICE:
            return await self.handle_git(
                json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.request_id
            )

        elif json_request[IMPORT_SERVICE].lower() == MYMINIFACTORY_SERVICE:
            return await self.handle_myminifactory(
                json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.request_id
            )

        elif json_request[IMPORT_SERVICE].lower() == GOOGLEDRIVE_SERVICE:
            return await self.handle_googledrive(
                json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.request_id
            )
        elif json_request[IMPORT_SERVICE].lower() == WIKIFACTORY_SERVICE:
            return await self.handle_wikifactory(
                json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.request_id
            )
        else:
            raise NotImplementedError()

    async def handle_thingiverse(self, url, auth_token, request_id):
        imp = ThingiverseImporter(request_id)
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

    async def handle_wikifactory(self, url, auth_token, request_id):
        imp = WikifactoryImporter(request_id)
        return await imp.process_url(url, auth_token)
