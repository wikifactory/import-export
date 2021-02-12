from app.model.exporter import Exporter
from app.config import wikifactory_connection_url
from gql import Client
from gql.transport.requests import RequestsHTTPTransport

from app.controller.error import NotValidManifest, ExportNotReachable
from app.models import (
    get_job,
    increment_processed_element_for_job,
    StatusEnum,
)

from .wikifactory_gql import (
    project_query,
    file_mutation,
    operation_mutation,
    complete_file_mutation,
    commit_contribution_mutation,
)

import requests
import magic

import os
import pygit2

import base64

endpoint_url = wikifactory_connection_url


def validate_url(url):

    from re import search

    pattern = (
        r"^(?:http(s)?:\/\/)?(www\.)?wikifactory\.com\/[@+][\w-]+\/[\w-]+$"
    )
    return bool(search(pattern, url))


class WikifactoryExporter(Exporter):
    def __init__(self, job_id):

        # Assign this import process a unique id
        # This id will identify the tmp folder

        self.job_id = job_id
        self.set_status(StatusEnum.exporting.value)

        self.manifest = None
        self.project_details = None

        self.add_hook_for_status(
            StatusEnum.exporting_successfully.value, self.on_files_uploaded
        )
        self.add_hook_for_status(
            StatusEnum.exporting_successfully.value,
            self.invite_collaborators,
        )

    def export_manifest(self, manifest):
        job = get_job(self.job_id)

        print("WIKIFACTORY: Starting the exporting process")

        # Extract the space and slug from the URL
        url_parts = export_url.split("/")
        space = url_parts[-2]
        slug = url_parts[-1]

        self.project_details = self.get_project_details(
            space, slug, job.export_token
        )

        # Check if we have a manifest
        if (
            self.manifest is not None
            and manifest.elements is not None
            and len(manifest.elements) > 0
        ):

            self.project_path = manifest.elements[0].path

            self.manifest.iterate_through_elements(
                self, self.on_file_cb, self.on_folder_cb, self.on_finished_cb
            )

            self.set_status(StatusEnum.exporting_successfully.value)

            return {"exported": "true", "manifest": self.manifest.toJson()}

        else:
            raise NotValidManifest("Manifest not valid")

    def on_file_cb(self, file_element):

        file_name = file_element.path.split("/")[-1]

        file_result = self.process_element(
            file_element, file_name, self.project_path, self.export_token
        )

        # Check that we got the right results
        if len(file_result["file"]["userErrors"]) > 0:

            for err in file_result["file"]["userErrors"]:
                print(err)
            return

        wikifactory_file_id = file_result["file"]["file"]["id"]
        s3_upload_url = file_result["file"]["file"]["uploadUrl"]

        if wikifactory_file_id is not None:

            # We actually have the id, move to the next step

            # 2) Upload to S3
            if s3_upload_url is not None and (len(s3_upload_url) > 0):
                with open(file_element.path, "rb") as data:
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
                    self.project_details.space_id,
                    wikifactory_file_id,
                    self.export_token,
                )

                # Increment the processed elements in the database
                increment_processed_element_for_job(self.job_id)

            else:
                raise Exception("WARNING: There is no S3 url")

                # Increment in any case the processed element
                increment_processed_element_for_job(self.job_id)

        else:
            print("WARNING: For some reason, the file id is None ")
            pass

    def on_folder_cb(self, folder_element):
        print("Ignoring folder element")

    def on_finished_cb(self):

        print("COMMIT")
        # In order to finish, I need to perform the commit
        self.commit_contribution(self.export_token)

    def wikifactory_api_request(
        self, wikifactory_query: str, export_token: str, variables: object
    ):
        transport = RequestsHTTPTransport(
            url=endpoint_url,
            headers={
                "Authorization": f"Bearer {export_token}",
            },
        )
        session = Client(
            transport=transport, fetch_schema_from_transport=False
        )

        result = session.execute(wikifactory_query, variable_values=variables)
        return result

    def process_element(self, element, file_name, project_path, export_token):

        variables = {
            "fileInput": {
                "filename": file_name,
                "spaceId": self.project_details.space_id,
                "size": os.path.getsize(element.path),
                "projectPath": element.path.replace(project_path, "")[1:],
                "gitHash": self.calculate_githash_for_element(element),
                "completed": "false",
                "contentType": magic.from_file(element.path, mime=True),
            }
        }

        return self.wikifactory_api_request(
            file_mutation,
            export_token,
            variables,
        )

    def get_project_details(self, space, slug, export_token):

        variables = {"space": space, "slug": slug}

        result = self.wikifactory_api_request(
            project_query, export_token, variables
        )

        if result is None or "userErrors" in result:
            raise ExportNotReachable("Project nof found in Wikifactory")

        return {
            "project_id": result["project"]["result"]["id"],
            "space_id": result["project"]["result"]["inSpace"]["id"],
            "private": result["project"]["result"]["private"],
        }

    def perform_mutation_operation(
        self, element, file_id, project_path, export_token
    ):

        variables = {
            "operationData": {
                "fileId": file_id,
                "opType": "ADD",
                "path": element.path.replace(project_path, "")[1:],
                "projectId": self.project_details.project_id,
            }
        }

        self.wikifactory_api_request(
            operation_mutation,
            export_token,
            variables,
        )

    def upload_file(self, file_handle, file_url):

        headers = {
            "x-amz-acl": "private"
            if self.project_details.private
            else "public-read",
            "Content-Type": magic.from_file(local_path, mime=True),
        }

        response = requests.put(file_url, data=data, headers=headers)

        if response.status_code != 200:
            raise FileUploadError(
                f"There was an error uploading the file. Error code: {response.status_code}"
            )
        print("File {} uploaded to s3".format(local_path.split("/")[-1]))

    def complete_file(self, space_id, file_id, export_token):

        variables = {
            "fileInput": {
                "spaceId": space_id,
                "id": file_id,
                "completed": True,
            }
        }
        result = self.wikifactory_api_request(
            complete_file_mutation,
            export_token,
            variables,
        )

        print(result)

    def commit_contribution(self, export_token):

        variables = {
            "commitData": {
                "projectId": self.project_details.project_id,
                "title": "Import files",
                "description": "",
            }
        }

        result = self.wikifactory_api_request(
            commit_contribution_mutation,
            export_token,
            variables,
        )
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

    def calculate_githash_for_element(self, element):
        return str(pygit2.hashfile(element.path))
