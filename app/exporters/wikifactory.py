import os
from re import search
from typing import IO, Dict, Optional

import magic
import pygit2
import requests
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from requests.models import HTTPError
from sqlalchemy.orm import Session

from app import crud
from app.exporters.base import AuthRequired, BaseExporter, NotReachable
from app.models.job import JobStatus

from .wikifactory_gql import (
    commit_contribution_mutation,
    complete_file_mutation,
    file_mutation,
    operation_mutation,
    project_query,
)

endpoint_url = "https://wikifactory.com/api/graphql"


class FileUploadFailed(Exception):
    pass


class NoResult(Exception):
    pass


class UserErrors(Exception):
    pass


def wikifactory_api_request(
    graphql_document: str,
    auth_token: str,
    variables: object,
    result_path: str,
) -> Dict:
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
    transport = RequestsHTTPTransport(
        url=endpoint_url,
        headers=headers,
    )

    session = Client(transport=transport, fetch_schema_from_transport=False)

    try:
        # FIXME - this seems to be a sync request. In the future,
        # we should look into making requests async
        execution_result = session.execute(graphql_document, variable_values=variables)
    except HTTPError as http_error:
        if http_error.response.status_code is requests.codes["unauthorized"]:
            raise AuthRequired
        raise NotReachable(http_error)
    except Exception as gql_error:
        error_message = str(gql_error)
        unauthorized_messages = ["unauthorized", "token is invalid"]

        for message in unauthorized_messages:
            if message in error_message:
                raise AuthRequired

        raise NotReachable(error_message)

    result_path_root, *result_path_rest = result_path.split(".")

    try:
        result = execution_result[result_path_root]
    except KeyError:
        raise NoResult()

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
                raise AuthRequired()
        raise UserErrors()

    try:
        for result_path_item in result_path_rest:
            result = result[result_path_item]
    except KeyError:
        raise NoResult()

    return result


wikifactory_project_regex = r"^(?:http(s)?:\/\/)?(www\.)?wikifactory\.com\/(?P<space>[@+][\w-]+)\/(?P<slug>[\w-]+)$"


def validate_url(url: str) -> bool:
    return bool(search(wikifactory_project_regex, url))


def space_slug_from_url(url: str) -> Dict:
    match = search(wikifactory_project_regex, url)
    assert match
    return match.groupdict()


class WikifactoryExporter(BaseExporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        self.project_details: Optional[Dict] = None

    def process(self) -> None:
        job = crud.job.get(self.db, self.job_id)
        assert job

        crud.job.update_status(self.db, db_obj=job, status=JobStatus.EXPORTING)

        self.project_details = self.get_project_details()
        assert self.project_details

        try:
            for (dirpath, _, filenames) in os.walk(job.path):
                for name in filenames:
                    file_path = os.path.join(dirpath, name)
                    self.on_file_cb(file_path)

            self.on_finished_cb()

            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.EXPORTING_SUCCESSFULLY
            )
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.FINISHED_SUCCESSFULLY
            )
        except (FileUploadFailed, UserErrors):

            # FIXME - improve error handling
            crud.job.update_status(
                self.db, db_obj=job, status=JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE
            )

    def on_file_cb(self, file_path: str) -> None:

        try:
            file_result = self.process_file(file_path)
        except UserErrors:
            raise FileUploadFailed("Wikifactory file couldn't be created")

        wikifactory_file_id = file_result.get("id")

        if not wikifactory_file_id:
            raise FileUploadFailed(
                "Wikifactory file couldn't be created. Missing File ID"
            )

        s3_upload_url = file_result["uploadUrl"]

        if not s3_upload_url:
            # FIXME - this mean the file already exists on Wikifactory.
            # We should probably query the "completed" status or raise an exception.
            print(
                "WARNING: There is no S3 url. This probably means a file with the same hash has already been uploaded"
            )
        else:
            # Upload to S3
            with open(file_path, "rb") as data:
                self.upload_file(data, s3_upload_url)

            # Once finished do the ADD operation
            self.perform_mutation_operation(
                file_path,
                wikifactory_file_id,
            )

            # Mark the file as completed
            self.complete_file(wikifactory_file_id)

            # Update the exported items
            crud.job.increment_exported_items(self.db, job_id=self.job_id)

    def on_finished_cb(self) -> None:
        # In order to finish, I need to perform the commit
        job = crud.job.get(self.db, self.job_id)
        assert job
        assert self.project_details

        variables = {
            "commitData": {
                "projectId": self.project_details["project_id"],
                "title": "Import files",
                "description": "",
            }
        }

        wikifactory_api_request(
            commit_contribution_mutation,
            job.export_token,
            variables,
            "commit.project",
        )

    def process_file(self, path: str) -> Dict:
        job = crud.job.get(self.db, self.job_id)
        assert job
        assert self.project_details

        variables = {
            "fileInput": {
                "filename": os.path.basename(path),
                "spaceId": self.project_details["space_id"],
                "size": os.path.getsize(path),
                "projectPath": os.path.relpath(path, job.path),
                "gitHash": str(pygit2.hashfile(path)),
                "completed": False,
                "contentType": magic.from_file(path, mime=True),
            }
        }

        return wikifactory_api_request(
            file_mutation, job.export_token, variables, "file.file"
        )

    def get_project_details(self) -> Dict:
        job = crud.job.get(self.db, self.job_id)
        assert job

        variables = space_slug_from_url(job.export_url)

        try:
            project = wikifactory_api_request(
                project_query, job.export_token, variables, "project.result"
            )
        except (NoResult, UserErrors):
            raise NotReachable("Project not found in Wikifactory")

        return {
            "project_id": project["id"],
            "space_id": project["inSpace"]["id"],
            "private": project["private"],
        }

    def perform_mutation_operation(self, file_path: str, file_id: str) -> None:
        job = crud.job.get(self.db, self.job_id)
        assert job
        assert self.project_details

        variables = {
            "operationData": {
                "fileId": file_id,
                "opType": "ADD",
                "path": os.path.relpath(file_path, job.path),
                "projectId": self.project_details["project_id"],
            }
        }

        wikifactory_api_request(
            operation_mutation,
            job.export_token,
            variables,
            "operation.project",
        )

    def upload_file(self, file_handle: IO, file_url: str) -> None:
        assert self.project_details

        headers = {
            "x-amz-acl": "private"
            if self.project_details["private"]
            else "public-read",
            "Content-Type": magic.from_descriptor(file_handle.fileno(), mime=True),
        }

        try:
            response = requests.put(file_url, data=file_handle, headers=headers)
            response.raise_for_status()
        except HTTPError:
            raise FileUploadFailed(
                f"There was an error uploading the file. Error code: {response.status_code}"
            )

        file_name = os.path.basename(file_handle.name)
        print(f"File {file_name} uploaded to s3")

    def complete_file(self, file_id: str) -> None:
        job = crud.job.get(self.db, self.job_id)
        assert job
        assert self.project_details

        variables = {
            "fileInput": {
                "id": file_id,
                "spaceId": self.project_details["space_id"],
                "completed": True,
            }
        }
        wikifactory_api_request(
            complete_file_mutation,
            job.export_token,
            variables,
            "file.file",
        )
