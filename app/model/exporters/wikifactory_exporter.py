from app.model.exporter import Exporter
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from app.model.element import ElementType
from app.model.exporter import ExporterStatus, NotValidManifest

import requests
import magic
import time
import os


user_id = "testuser3"  # QUESTION: Where do I get this?
client_username = "dGVzdHVzZXIz"  # QUESTION: Where do I get this?
project_name = "exporttest2"  # QUESTION: Where do I get this?
project_id = "UHJvamVjdDo0NDMxOTI="  # QUESTION: Where do I get this?
space_id = "U3BhY2U6ODU5NDc="  # QUESTION: Where do I get this?

export_url = "http://localweb:8080/@{}/{}".format(user_id, project_name)


endpoint_url = "http://localweb:8080/api/graphql"


class WikifactoryMutations:
    file_mutation = gql(
        """
        mutation File($fileInput: FileInput) {
            file (fileData: $fileInput) {
                file {
                    id
                    path
                    mimeType
                    filename
                    size
                    completed
                    cancelled
                    isCopy
                    slug
                    spaceId
                    uploadUrl
                }

                userErrors {
                    message
                    key
                    code
                }

            }
        }
        """
    )

    operation_mutation = gql(
        """
        mutation Operation($operationData: OperationInput) {
            operation(operationData: $operationData) {
                project {
                    id
                }
            }
        }
        """
    )

    complete_file_mutation = gql(
        """
        mutation CompleteFile($fileInput: FileInput) {
        file(fileData: $fileInput) {
            file {
                id
                path
                url
                completed
            }
            userErrors {
                message
                key
                code
            }
        }
    }
        """
    )

    commit_contribution_mutation = gql(
        """
        mutation CommitContribution($commitData: CommitInput) {
            commit(commitData: $commitData) {
                project {
                    id
                    inSpace {
                        id
                        whichTypes
                    }
                    contributionCount
                }
                userErrors {
                    message
                    key
                    code
                }
            }
        }
        """
    )


class WikifactoryExporter(Exporter):
    def __init__(self, request_id):

        # Assign this import process a unique id
        # This id will identify the tmp folder
        self.request_id = request_id
        self.set_status(ExporterStatus.INITIALIZED)

        self.manifest = None

        self.add_hook_for_status(ExporterStatus.FILES_UPLOADED, self.on_files_uploaded)
        self.add_hook_for_status(
            ExporterStatus.FILES_UPLOADED, self.invite_collaborators
        )

    def validate_url(url):

        pattern = (
            "^(?:http(s)?:\/\/)?(www\.)?wikifactory\.com\/(\@|\+)[\w\-º_]*\/[\w\-\_]+$"
        )
        import re

        result = re.search(pattern, url)

        if result is None:
            return False
        else:
            return True

    async def export_manifest(self, manifest, export_url, export_token):

        print("WIKIFACTORY: Starting the exporting process")

        """
        # Extract the space and slug from the URL
        url_parts = export_url.split("/")
        space = url_parts[-2]
        slug = url_parts[-1]
        """
        self.manifest = manifest

        # Check if we have a manifest
        if manifest is not None:

            root_element = manifest.elements[0]

            # Get the path of the root folder
            project_path = root_element.path

            # Init the queue for the files
            elements_queue = []

            self.set_status(ExporterStatus.UPLOADING_FILES)

            for e in root_element.children:
                elements_queue.append(e)

            while len(elements_queue) > 0:

                element = elements_queue.pop(0)
                file_name = element.path.split("/")[-1]

                if element.type == ElementType.FOLDER:
                    # It is a folder, ignore it but add its files to the queue
                    for ch_element in element.children:
                        elements_queue.append(ch_element)

                else:
                    # It is a file

                    # Perform all the steps for this element / file

                    # First, execute the file mutation
                    file_result = await self.process_element(
                        element, file_name, project_path, export_token
                    )

                    # Check that we got the right results
                    if len(file_result["file"]["userErrors"]) > 0:
                        print("Errors")

                        for i in len(file_result["file"]["userErrors"]):
                            print(file_result["file"]["userErrors"])
                        return

                    wikifactory_file_id = file_result["file"]["file"]["id"]
                    s3_upload_url = file_result["file"]["file"]["uploadUrl"]

                    if wikifactory_file_id is not None:

                        # We actually have the id, move to the next step

                        # 2) Upload to S3
                        if s3_upload_url is not None and (len(s3_upload_url) > 0):
                            self.upload_file(element.path, s3_upload_url)

                            # 3) Once finished do the ADD operation

                            await self.perform_mutation_operation(
                                element, wikifactory_file_id, project_path
                            )

                            # 4) Finally, mark the file as completed

                            await self.complete_file(space_id, wikifactory_file_id)

                        else:
                            print("WARNING: There is no S3 url")

                    else:
                        print("WARNING: For some reason, we don't ")
                        pass

            # Once I have finished with all the files, perform the last step.
            # Do the contribution
            self.set_status(ExporterStatus.FILES_UPLOADED)
            return await self.commit_contribution()

        else:
            raise NotValidManifest()

    async def process_element(self, element, file_name, project_path, export_token):

        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )

        async with Client(
            transport=transport, fetch_schema_from_transport=True
        ) as session:

            # FIX: the projectPath should be the path using the folders,
            # not the name
            variables = {
                "fileInput": {
                    "filename": file_name,
                    "spaceId": space_id,
                    "size": os.path.getsize(element.path),
                    "projectPath": element.path.replace(project_path, "")[1:],
                    "gitHash": str(int(round(time.time() * 1000))),
                    "completed": "false",
                    "contentType": magic.from_file(element.path, mime=True),
                }
            }

            print(variables)

            result = await session.execute(
                WikifactoryMutations.file_mutation, variable_values=variables
            )

            return result

    async def perform_mutation_operation(self, element, file_id, project_path):
        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(token),
            },
        )

        async with Client(
            transport=transport, fetch_schema_from_transport=True
        ) as session:

            variables = {
                "operationData": {
                    "fileId": file_id,
                    "opType": "ADD",
                    "path": element.path.replace(project_path, "")[1:],
                    "projectId": project_id,
                }
            }

            result = await session.execute(
                WikifactoryMutations.operation_mutation, variable_values=variables
            )
            print("OPERATION ADD done")
            print(result)

    def upload_file(self, local_path, file_url):

        headers = {
            "x-amz-acl": "public-read",
            "Content-Type": magic.from_file(local_path, mime=True),
        }

        with open(local_path, "rb") as data:
            response = requests.put(file_url, data=data, headers=headers)
            if response.status_code != 200:
                print(
                    "There was an error uploading the file. Error code: {}".format(
                        response.status_code
                    )
                )
                print(response.content)
            else:
                print("UPLOADED TO S3")

    async def complete_file(self, space_id, file_id):
        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(token),
            },
        )

        async with Client(
            transport=transport, fetch_schema_from_transport=True
        ) as session:

            variables = {
                "fileInput": {"spaceId": space_id, "id": file_id, "completed": True}
            }

            result = await session.execute(
                WikifactoryMutations.complete_file_mutation, variable_values=variables
            )
            print("Complete file mutation done")
            print(result)

    async def commit_contribution(self):

        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(token),
            },
        )

        async with Client(
            transport=transport, fetch_schema_from_transport=True
        ) as session:

            variables = {
                "commitData": {
                    "projectId": project_id,
                    "title": "Test",
                    "description": "descrp",
                }
            }

            result = await session.execute(
                WikifactoryMutations.commit_contribution_mutation,
                variable_values=variables,
            )
            print("Commit mutation done")
            print(result)

    def on_files_uploaded(self):
        print("------------------")
        print("  FILES UPLOADED  ")
        print("------------------")

    def invite_collaborators(self):

        if self.manifest is not None:

            emails_list = self.manifest.collaborators

            for addres in emails_list:

                print(addres)

