from app.model.exporter import Exporter
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from app.model.exporter import ExporterStatus, NotValidManifest

import requests
import magic
import time
import os


user_id = "testuseradmin"  # QUESTION: Where do I get this?
client_username = "dGVzdHVzZXJhZG1pbg=="  # QUESTION: Where do I get this?
project_name = "testproject2"  # QUESTION: Where do I get this?

export_url = "http://192.168.50.102:8080/@{}/{}".format(user_id, project_name)


endpoint_url = "http://192.168.50.102:8080/api/graphql"


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

    project_query = gql(
        """query q($space:String, $slug:String){
            project(space:$space, slug:$slug){
                result{
                    id
                    space {
                        id
                    }
                    inSpace {
                        id
                    }
                }
            }
        }"""
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

        self.space_id = ""
        self.project_id = ""

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

    def export_manifest(self, manifest, export_url, export_token):

        print("WIKIFACTORY: Starting the exporting process")

        # Extract the space and slug from the URL
        url_parts = export_url.split("/")
        space = url_parts[-2]
        slug = url_parts[-1]

        self.manifest = manifest
        self.export_token = export_token

        # TODO: Get the details of the project: project_id, space_id

        details = self.get_project_details(space, slug, export_token)

        if details is None:
            return {}

        self.project_id = details[0]
        self.space_id = details[1]

        # Check if we have a manifest
        if manifest is not None:

            self.project_path = manifest.elements[0].path

            manifest.iterate_through_elements(
                self, self.on_file_cb, self.on_folder_cb, self.on_finished_cb
            )
            return {"exported": "true", "manifest": manifest.toJson()}

        else:
            raise NotValidManifest()

    def on_file_cb(self, file_element):

        print("FILE!")
        print(file_element.path)

        file_name = file_element.path.split("/")[-1]

        file_result = self.process_element(
            file_element, file_name, self.project_path, self.export_token
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
                self.upload_file(file_element.path, s3_upload_url)

                # 3) Once finished do the ADD operation

                self.perform_mutation_operation(
                    file_element,
                    wikifactory_file_id,
                    self.project_path,
                    self.export_token,
                )

                # 4) Finally, mark the file as completed

                self.complete_file(
                    self.space_id, wikifactory_file_id, self.export_token
                )

            else:
                print("WARNING: There is no S3 url")

        else:
            print("WARNING: For some reason, we don't ")
            pass

    def on_folder_cb(self, folder_element):
        print("Ignoring folder element")

    def on_finished_cb(self):

        print("COMMIT")
        print(self.export_token)
        # In order to finish, I need to perform the commit
        self.commit_contribution(self.export_token)

    def process_element(self, element, file_name, project_path, export_token):

        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )

        session = Client(transport=transport, fetch_schema_from_transport=True)
        # FIX: the projectPath should be the path using the folders,
        # not the name
        variables = {
            "fileInput": {
                "filename": file_name,
                "spaceId": self.space_id,
                "size": os.path.getsize(element.path),
                "projectPath": element.path.replace(project_path, "")[1:],
                "gitHash": str(int(round(time.time() * 1000))),
                "completed": "false",
                "contentType": magic.from_file(element.path, mime=True),
            }
        }

        print(variables)

        result = session.execute(
            WikifactoryMutations.file_mutation, variable_values=variables
        )

        return result
        """async with Client(
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
        """

    def get_project_details(self, space, slug, export_token):
        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )
        session = Client(transport=transport, fetch_schema_from_transport=True)
        variables = {"space": space, "slug": slug}

        result = session.execute(
            WikifactoryMutations.project_query, variable_values=variables
        )

        if "userErrors" not in result:
            p_id = result["project"]["result"]["id"]
            sp_id = result["project"]["result"]["inSpace"]["id"]

            return (p_id, sp_id)
        else:
            print("PROJECT NOT FOUND INSIDE WIKIFACTORY")
            # TODO: Raise custom exception
            return None

    def perform_mutation_operation(self, element, file_id, project_path, export_token):
        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )

        session = Client(transport=transport, fetch_schema_from_transport=True)
        variables = {
            "operationData": {
                "fileId": file_id,
                "opType": "ADD",
                "path": element.path.replace(project_path, "")[1:],
                "projectId": self.project_id,
            }
        }

        result = session.execute(
            WikifactoryMutations.operation_mutation, variable_values=variables
        )
        print("OPERATION ADD done")
        print(result)

        """
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
        """

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

    def complete_file(self, space_id, file_id, export_token):
        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )

        session = Client(transport=transport, fetch_schema_from_transport=True)
        variables = {
            "fileInput": {"spaceId": space_id, "id": file_id, "completed": True}
        }

        result = session.execute(
            WikifactoryMutations.complete_file_mutation, variable_values=variables
        )
        print("Complete file mutation done")
        print(result)
        """
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
        """

    def commit_contribution(self, export_token):

        transport = AIOHTTPTransport(
            url=endpoint_url,
            headers={
                "CLIENT-USERNAME": client_username,
                "Cookie": "session={}".format(export_token),
            },
        )

        session = Client(transport=transport, fetch_schema_from_transport=True)
        variables = {
            "commitData": {
                "projectId": self.project_id,
                "title": "Test",
                "description": "descrp",
            }
        }

        result = session.execute(
            WikifactoryMutations.commit_contribution_mutation, variable_values=variables
        )
        print("Commit mutation done")
        print(result)
        """
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
        """

    def on_files_uploaded(self):
        print("------------------")
        print("  FILES UPLOADED  ")
        print("------------------")

    def invite_collaborators(self):

        if self.manifest is not None:

            emails_list = self.manifest.collaborators

            for addres in emails_list:

                print(addres)

