import requests
import magic

import os
import pygit2

import base64

from app.model.exporter import Exporter
from app.config import wikifactory_connection_url
from gql import Client
from gql.transport.requests import RequestsHTTPTransport

from app.controller.error import (
    NotValidManifest,
    ExportNotReachable,
    FileUploadError,
    ExportAuthRequired,
    WikifactoryAPIUserErrors,
    WikifactoryAPINoResultPath,
    WikifactoryAPINoResult,
)
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

endpoint_url = wikifactory_connection_url


def wikifactory_api_request(
    graphql_document: str,
    auth_token: str,
    variables: object,
    result_path: str,
):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
    transport = RequestsHTTPTransport(
        url=endpoint_url,
        headers=headers,
    )
    session = Client(transport=transport, fetch_schema_from_transport=False)

    try:
        # FIXME - this seems to be a sync request. In the future,
        # we should look into making requests async
        execution_result = session.execute(
            graphql_document, variable_values=variables
        )
    except requests.HTTPError as http_error:
        if http_error.response.status_code == requests.codes["unauthorized"]:
            raise ExportAuthRequired()
        raise http_error

    try:
        result_path_root, *result_path_rest = result_path.split(".")
    except AttributeError:
        raise WikifactoryAPINoResultPath()

    if execution_result.errors:
        for error in execution_result.errors:
            if "unauthorized request" in error.get(
                "message"
            ) or "token is invalid" in error.get("message"):
                raise ExportAuthRequired()
        # FIXME trigger an exception on other GraphQL errors?

    try:
        result = execution_result.data[result_path_root]
    except KeyError:
        raise WikifactoryAPINoResult()

    user_errors = result.get("userErrors", [])
    if user_errors:
        for error in user_errors:
            if error.get("code") in [
                "AUTHORISATION",
                "AUTHENTICATION",
                "NOTFOUND",
            ]:
                # FIXME NOTFOUND should either be handled differently or
                # the error code should be passed to the exception, so a "real" NOTFOUND
                # can be differentiated from a "not allowed to read right now"
                raise ExportAuthRequired()
        raise WikifactoryAPIUserErrors()

    try:
        for result_path_item in result_path_rest:
            result = result[result_path_item]
    except KeyError:
        raise WikifactoryAPINoResult()

    return result


def validate_url(url):

    from re import search

    pattern = (
        r"^(?:http(s)?:\/\/)?(www\.)?wikifactory\.com\/[@+][\w-]+\/[\w-]+$"
    )
    return bool(search(pattern, url))


class WikifactoryExporter(Exporter):
    def __init__(self, job_id):
        self.job_id = job_id
        self.set_status(StatusEnum.exporting.value)

        self.manifest = None
        self.project_details = None

    def export_manifest(self, manifest):

        job = get_job(self.job_id)
        print("WIKIFACTORY: Starting the exporting process")

        # Extract the space and slug from the URL
        url_parts = job.export_url.split("/")
        space = url_parts[-2]
        slug = url_parts[-1]

        self.project_details = self.get_project_details(space, slug)

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

        try:
            file_result = self.process_element(file_element, file_name)
        except WikifactoryAPIUserErrors:
            raise FileUploadError("Wikifactory file couldn't be created")

        wikifactory_file_id = file_result["file"]["file"]["id"]

        if not wikifactory_file_id:
            raise FileUploadError(
                "Wikifactory file couldn't be created. Missing File ID"
            )

        s3_upload_url = file_result["file"]["file"]["uploadUrl"]

        if not s3_upload_url:
            print(
                "WARNING: There is no S3 url. This probably means a file with the same hash has already been uploaded"
            )

        # 2) Upload to S3
        with open(file_element.path, "rb") as data:
            self.upload_file(data, s3_upload_url)

        # 3) Once finished do the ADD operation
        self.perform_mutation_operation(
            file_element,
            wikifactory_file_id,
        )

        # 4) Finally, mark the file as completed
        self.complete_file(wikifactory_file_id)

        # Increment the processed elements in the database
        increment_processed_element_for_job(self.job_id)

    def on_folder_cb(self, folder_element):
        print("Ignoring folder element")

    def on_finished_cb(self):
        # In order to finish, I need to perform the commit
        self.commit_contribution()

    def process_element(self, element, file_name):
        job = get_job(self.job_id)

        variables = {
            "fileInput": {
                "filename": file_name,
                "spaceId": self.project_details["space_id"],
                "size": os.path.getsize(element.path),
                "projectPath": os.path.relpath(
                    element.path, self.project_path
                ),
                "gitHash": str(pygit2.hashfile(element.path)),
                "completed": "false",
                "contentType": magic.from_file(element.path, mime=True),
            }
        }

        return wikifactory_api_request(
            file_mutation, job.export_token, variables, "fileInput"
        )

    def get_project_details(self, space, slug):

        job = get_job(self.job_id)

        variables = {"space": space, "slug": slug}

        try:
            project = wikifactory_api_request(
                project_query, job.export_token, variables, "project"
            )
        except:
            raise ExportNotReachable("Project nof found in Wikifactory")

        return {
            "project_id": project["id"],
            "space_id": project["inSpace"]["id"],
            "private": project["private"],
        }

    def perform_mutation_operation(self, element, file_id):

        variables = {
            "operationData": {
                "fileId": file_id,
                "opType": "ADD",
                "path": os.path.relpath(element.path, self.project_path),
                "projectId": self.project_details["project_id"],
            }
        }

        wikifactory_api_request(
            operation_mutation, self.export_token, variables, "operationData"
        )

    def upload_file(self, file_handle, file_url):

        headers = {
            "x-amz-acl": "private"
            if self.project_details["private"]
            else "public-read",
            "Content-Type": magic.from_descriptor(
                file_handle.fileno(), mime=True
            ),
        }

        response = requests.put(file_url, data=file_handle, headers=headers)

        if response.status_code != 200:
            raise FileUploadError(
                f"There was an error uploading the file. Error code: {response.status_code}"
            )

        file_name = os.path.basename(file_handle.name)
        print(f"File {file_name} uploaded to s3")

    def complete_file(self, file_id):
        job = get_job(self.job_id)

        variables = {
            "fileInput": {
                "spaceId": self.project_details["space_id"],
                "id": file_id,
                "completed": True,
            }
        }
        self.wikifactory_api_request(
            complete_file_mutation,
            job.export_token,
            variables,
            "fileInput",
        )

    def commit_contribution(self):

        job = get_job(self.job_id)

        variables = {
            "commitData": {
                "projectId": self.project_details["project_id"],
                "title": "Import files",
                "description": "",
            }
        }

        self.wikifactory_api_request(
            commit_contribution_mutation,
            job.export_token,
            variables,
            "commitData",
        )
