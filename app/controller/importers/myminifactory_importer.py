from app.model.importer import Importer

from app.model.constants import MYMINIFACTORY_URL
from app.model.manifest import Manifest
from app.model.thing import Thing


class MyMiniFactoryImporter(Importer):
    def __init__(self, request_id):
        self.request_id = request_id

    def process_url(self, url, auth_token):
        print("Myminifactory: Starting process of URL:")
        print(url)
        basic_info = self.retrieve_basic_object_info(url, auth_token)
        pass

    def retrieve_basic_object_info(self, url, auth_token):

        # TODO: extract the required info from the url
        pass
