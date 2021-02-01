from app.model.importer import Importer
import os

# import aiohttp
# from app.model.constants import THINGIVERSE_URL, THINGIVERSE_THINGS_PATH

from app.model.manifest import Manifest
from app.model.thing import Thing
from app.models import StatusEnum


class AppTokenError(Exception):
    def __init__(self, message="Could not find the env var App token"):
        super().__init__(self.message)


class ThingiverseImporter(Importer):
    def __init__(self, job_id):
        self.app_token = os.getenv("THINGIVERSE_APP_TOKEN")
        self.job_id = job_id
        if self.app_token is None:
            raise AppTokenError()
        else:
            pass

    def process_url(self, url, auth_token):
        print("THINGIVERSE: Starting process of URL:")

        # TODO: validate the URL

        basic_thing_info = self.retrieve_basic_thing_info(url, auth_token)
        # TODO: Check for empty values (None)

        # Create the Manifest that will be later exported
        manifest = Manifest()

        # Populate the manifest using the retrieved information
        # Initially, each imported "thing" will be exported as a
        # thing of the manifest
        self.populate_manifest_with_things(manifest, [basic_thing_info])

        # Finally, set the status
        self.set_status(StatusEnum.importing_successfully.value)
        return manifest

    def retrieve_basic_thing_info(self, url, auth_token):
        # Extract the ID of the thing, so we can later use the thingiverse API
        """url_components = url.split("/")

        thing_identifier_label = url_components[len(url_components) - 1]

        thing_id = thing_identifier_label.split(":")[1]

        thing_url = (
            THINGIVERSE_URL
            + THINGIVERSE_THINGS_PATH
            + thing_id
            + "?access_token="
            + self.app_token
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(thing_url) as response:
                json_result = await response.json()
                return json_result"""
        return {}

    def populate_manifest_with_things(self, manifest, things_arr):

        for thing in things_arr:

            new_thing = Thing()

            # TODO: Generate new id?
            new_thing.id = thing["id"]

            new_thing.title = thing["name"]
            new_thing.description = thing["description"]

            manifest.things.append(new_thing)
