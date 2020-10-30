from ..model.constants import THINGIVERSE_SERVICE, MYMINIFACTORY_SERVICE
from ..model.constants import GITHUB_SERVICE, GIT_SERVICE
from ..model.constants import SOURCE_URL, AUTH_TOKEN, SERVICE
from ..model.importers.thingiverse_importer import ThingiverseImporter
from ..model.importers.github_importer import GithubImporter
from ..model.importers.git_importer import GitImporter

class ImporterProxy:

    def __init__(self):
        pass

    async def handle_request(self, json_request):

        print(json_request)
        if(json_request[SERVICE].lower() == THINGIVERSE_SERVICE):

            return await self.handle_thingiverse(json_request[SOURCE_URL],
                                                 json_request[AUTH_TOKEN])

        elif(json_request[SERVICE].lower() == GITHUB_SERVICE):
            return await self.handle_github(json_request[SOURCE_URL],
                                            json_request[AUTH_TOKEN])

        elif(json_request[SERVICE].lower() == GIT_SERVICE):
            return await self.handle_git(json_request[SOURCE_URL],
                                         json_request[AUTH_TOKEN])

        elif(json_request[SERVICE].lower() == MYMINIFACTORY_SERVICE):
            return await self.handle_myminifactory(json_request[SOURCE_URL],
                                                   json_request[AUTH_TOKEN])
        else:
            raise NotImplementedError()

    async def handle_thingiverse(self, url, auth_token):
        imp = ThingiverseImporter()
        return await imp.process_url(url, auth_token)

    async def handle_github(self, url, auth_token):
        imp = GithubImporter()
        return await imp.process_url(url, auth_token)

    async def handle_git(self, url, auth_token):
        imp = GitImporter()
        return await imp.process_url(url, auth_token)

    async def handle_myminifactory(self, url, auth_token):
        imp = MyMiniFactoryImporter()
        return await imp.process_url(url, auth_token)
