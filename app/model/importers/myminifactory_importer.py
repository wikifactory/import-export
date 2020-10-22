from ..importer import Importer

from ..constants import MYMINIFACTORY_URL
from ..manifest import Manifest
from ..thing import Thing


class MyMiniFactoryImporter(Importer):

    def __init__(self):
        pass

    async def process_url(self, url, auth_token):
        print("Myminifactory: Starting process of URL:")
        print(url)
        basic_info = await self.retrieve_basic_object_info(url, auth_token)
        pass

    async def retrieve_basic_object_info(self, url, auth_token):

        # TODO: extract the required info from the url
        pass