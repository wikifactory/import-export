import os
from typing import Optional

import dropbox
from dropbox.dropbox_client import BadInputException, Dropbox
from dropbox.exceptions import ApiError, AuthError, HttpError
from sqlalchemy.orm import Session
from stone.backends.python_rsrc.stone_validators import ValidationError

from app import crud
from app.exporters.base import BaseExporter
from app.models.job import Job, JobStatus


class FileUploadFailed(Exception):
    pass


class MalformedDropboxURL(Exception):
    pass


CHUNK_SIZE = 5 * 1024 * 1024  # Size in bytes


class DropboxExporter(BaseExporter):
    def __init__(self, db: Session, job_id: str):
        self.db = db
        self.job_id = job_id
        self.dropbox_handler: Optional[Dropbox] = None

    def process(self) -> None:
        # Note: the Dropbox exporter will only accept endpoints with the following format:
        # https://www.dropbox.com/home/path/to/folder
        # Hence, shared links will not be accepted

        job: Job = crud.job.get(self.db, self.job_id)
        assert job

        crud.job.update_status(self.db, db_obj=job, status=JobStatus.EXPORTING)

        try:
            if len(job.export_token) == 0:
                # Use a default, not valid token
                self.dropbox_handler = dropbox.Dropbox(
                    oauth2_access_token="R2D2c3p0p4dm34n4k1n3Ia"
                )
            else:
                self.dropbox_handler = dropbox.Dropbox(
                    oauth2_access_token=job.export_token
                )
        except (BadInputException, HttpError, AuthError):
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.EXPORTING_ERROR_AUTHORIZATION_REQUIRED,
            )
            return

        try:
            self.upload_job_folder()
        except (FileUploadFailed, MalformedDropboxURL):
            crud.job.update_status(
                self.db,
                db_obj=job,
                status=JobStatus.EXPORTING_ERROR_DATA_UNREACHABLE,
            )
            return

        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.EXPORTING_SUCCESSFULLY
        )
        crud.job.update_status(
            self.db, db_obj=job, status=JobStatus.FINISHED_SUCCESSFULLY
        )

        # Finally, remove the local files
        self.clean_download_folder(job.path)

    def upload_job_folder(self) -> None:

        job: Job = crud.job.get(self.db, self.job_id)

        path_to_local_files = job.path

        for dir, _, files in os.walk(path_to_local_files):

            for file in files:

                local_file_path = os.path.join(dir, file)
                destination_path = os.path.join(
                    job.export_url.replace("https://www.dropbox.com/home", ""),
                    os.path.relpath(local_file_path, path_to_local_files),
                )

                self.upload_file(local_file_path, destination_path)

                # Update the exported items
                crud.job.increment_exported_items(self.db, job_id=self.job_id)

    def upload_file(self, local_path: str, remote_path: str) -> None:

        assert self.dropbox_handler

        # IMPORTANT: The dropbox application must have the files.content.write permission
        try:

            with open(local_path, "rb") as f:

                file_size = os.path.getsize(local_path)

                if (
                    file_size <= CHUNK_SIZE
                ):  # Use the direct upload approach for small files

                    self.dropbox_handler.files_upload(f.read(), remote_path)
                else:  # Otherwise, use the session aproach

                    upload_session_start_result = (
                        self.dropbox_handler.files_upload_session_start(
                            f.read(CHUNK_SIZE)
                        )
                    )
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell(),
                    )
                    commit = dropbox.files.CommitInfo(path=remote_path)

                    while f.tell() < file_size:
                        if (file_size - f.tell()) <= CHUNK_SIZE:
                            self.dropbox_handler.files_upload_session_finish(
                                f.read(CHUNK_SIZE), cursor, commit
                            )
                        else:
                            self.dropbox_handler.files_upload_session_append(
                                f.read(CHUNK_SIZE), cursor.session_id, cursor.offset
                            )
                            cursor.offset = f.tell()

        except OSError as e:
            print("Error opening the local file")
            raise e

        except ApiError as e:
            print("Error uploading the file")
            raise FileUploadFailed(f"Error uploading file: {local_path}") from e

        except ValidationError as e:
            raise MalformedDropboxURL(
                "Maybe you are trying to import from a shared link?"
            ) from e
            return
