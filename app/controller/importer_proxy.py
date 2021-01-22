from app.model.constants import (
    THINGIVERSE_SERVICE,
    MYMINIFACTORY_SERVICE,
    WIKIFACTORY_SERVICE,
)
from app.model.constants import IMPORT_SERVICE, IMPORT_URL, IMPORT_TOKEN
from app.model.constants import GIT_SERVICE

from app.model.constants import GOOGLEDRIVE_SERVICE
from app.controller.importers.thingiverse_importer import ThingiverseImporter
from app.controller.importers.git_importer import GitImporter
from app.controller.importers.googledrive_importer import GoogleDriveImporter
from app.controller.importers.myminifactory_importer import MyMiniFactoryImporter
from app.controller.importers.wikifactory_importer import WikifactoryImporter

from app.models import set_number_of_files_for_job_id


class ImporterProxy:
    def __init__(self, job_id):
        self.job_id = job_id

    def handle_request(self, json_request):

        result_manifest = None
        try:

            if json_request[IMPORT_SERVICE].lower() == THINGIVERSE_SERVICE:

                result_manifest = self.handle_thingiverse(
                    json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.job_id
                )

            elif json_request[IMPORT_SERVICE].lower() == GIT_SERVICE:
                result_manifest = self.handle_git(
                    json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.job_id
                )

            elif json_request[IMPORT_SERVICE].lower() == MYMINIFACTORY_SERVICE:
                result_manifest = self.handle_myminifactory(
                    json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.job_id
                )

            elif json_request[IMPORT_SERVICE].lower() == GOOGLEDRIVE_SERVICE:
                result_manifest = self.handle_googledrive(
                    json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.job_id
                )
            elif json_request[IMPORT_SERVICE].lower() == WIKIFACTORY_SERVICE:
                result_manifest = self.handle_wikifactory(
                    json_request[IMPORT_URL], json_request[IMPORT_TOKEN], self.job_id
                )
            else:
                raise NotImplementedError()

            if result_manifest is not None:
                # TODO: Store the manifest in the DB
                # Store the manifest.file_elements associated to the job_id
                set_number_of_files_for_job_id(
                    self.job_id, result_manifest.file_elements
                )

                return result_manifest

        except Exception as e:
            print(e)
            return {"error": "Manifest is None"}

    def handle_thingiverse(self, url, auth_token, job_id):
        imp = ThingiverseImporter(job_id)
        return imp.process_url(url, auth_token)

    def handle_git(self, url, auth_token, job_id):
        imp = GitImporter(job_id)
        return imp.process_url(url, auth_token)

    def handle_googledrive(self, url, auth_token, job_id):
        imp = GoogleDriveImporter(job_id)
        return imp.process_url(url, auth_token)

    def handle_myminifactory(self, url, auth_token, job_id):
        imp = MyMiniFactoryImporter(job_id)
        return imp.process_url(url, auth_token)

    def handle_wikifactory(self, url, auth_token, job_id):
        imp = WikifactoryImporter(job_id)
        return imp.process_url(url, auth_token)
