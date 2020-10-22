from ..model.constants import THINGIVERSE_SERVICE
from ..model.constants import SOURCE_URL, AUTH_TOKEN, SERVICE
from ..model.importers.thingiverse_importer import ThingiverseImporter


class ImporterProxy:

    def __init__(self):
        pass

    async def handle_request(self, json_request):

        print(json_request)
        if(json_request[SERVICE].lower() == THINGIVERSE_SERVICE):

            return await self.handle_thingiverse(json_request[SOURCE_URL],
                                                 json_request[AUTH_TOKEN])
        else:
            raise NotImplementedError()

    async def handle_thingiverse(self, url, auth_token):
        imp = ThingiverseImporter()
        return await imp.process_url(url, auth_token)
