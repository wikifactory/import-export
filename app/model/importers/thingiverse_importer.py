from ..importer import Importer
import os
import aiohttp


from ..constants import THINGIVERSE_URL, THINGIVERSE_THINGS_PATH


class AppTokenError(Exception):
    def __init__(self, message="Could not find the env var App token"):
        super().__init__(self.message)


class ThingiverseImporter(Importer):

    def __init__(self):
        self.app_token = os.getenv("THINGIVERSE_APP_TOKEN")

        if(self.app_token is None):
            raise AppTokenError()
        else:
            pass

    async def process_url(self, url, auth_token):
        print("THINGIVERSE: Starting process of URL:")
        print(url)
        # TODO: validate the URL

        # Extract the ID of the thing, so we can later use the thingiverse API
        url_components = url.split("/")

        thing_identifier_label = url_components[len(url_components) - 1]

        thing_id = thing_identifier_label.split(":")[1]

        thing_url = THINGIVERSE_URL + THINGIVERSE_THINGS_PATH + thing_id \
                                    + "/files?access_token=" + self.app_token

        async with aiohttp.ClientSession() as session:
            async with session.get(thing_url) as response:
                print(response.status)
                json_result = await response.json()
                print(json_result)

                # print(json_result["id"])
                # print(json_result["name"])
