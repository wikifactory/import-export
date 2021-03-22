import os
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import not_

from app.core.config import settings
from app.crud.base import CRUDBase
from app.models.job import (
    Job,
    JobDuplicated,
    JobNotCancellable,
    JobNotRetriable,
    JobStatus,
    can_export_job_statuses,
    can_import_job_statuses,
    retriable_job_statuses,
    terminated_job_statuses,
)
from app.models.job_log import JobLog
from app.schemas.job import JobCreate, JobUpdate


class CRUDJob(CRUDBase[Job, JobCreate, JobUpdate]):
    def create(self, db: Session, *, obj_in: JobCreate) -> Job:
        active_job_exists = (
            db.query(Job)
            .filter(
                Job.import_url == obj_in.import_url,
                Job.export_url == obj_in.export_url,
                not_(Job.status in terminated_job_statuses),
            )
            .one_or_none()
        )
        if active_job_exists:
            raise JobDuplicated()

        db_job = super().create(db, obj_in=obj_in)
        db_job.path = os.path.join(settings.JOBS_BASE_PATH, str(db_job.id))
        log_obj = JobLog(job_id=db_job.id, to_status=db_job.status)
        db.add(log_obj)
        db.commit()
        return db_job

    def update_status(self, db: Session, *, db_obj: Job, status: JobStatus) -> Job:
        if db_obj.status is status:
            pass

        log_obj = JobLog(job_id=db_obj.id, from_status=db_obj.status, to_status=status)
        db.add(log_obj)
        db_obj.status = status
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_total_items(self, db: Session, *, job_id: str, total_items: int) -> None:
        db.query(Job).filter(Job.id == job_id).update({Job.total_items: total_items})
        db.commit()

    def update_imported_items(
        self, db: Session, *, job_id: str, imported_items: int
    ) -> None:
        db.query(Job).filter(Job.id == job_id).update(
            {Job.imported_items: imported_items}
        )
        db.commit()

    def increment_imported_items(self, db: Session, *, job_id: str) -> None:
        db.query(Job).filter(Job.id == job_id).update(
            {Job.imported_items: Job.imported_items + 1}
        )
        db.commit()

    def increment_exported_items(self, db: Session, *, job_id: str) -> None:
        db.query(Job).filter(Job.id == job_id).update(
            {Job.exported_items: Job.exported_items + 1}
        )
        db.commit()

    def cancel(self, db: Session, *, db_obj: Job) -> Job:
        if not self.is_active(job=db_obj):
            raise JobNotCancellable()

        # mark the job as cancelling
        self.update_status(db, db_obj=db_obj, status=JobStatus.CANCELLING)

        return db_obj

    def retry(
        self, db: Session, *, db_obj: Job, retry_input: Optional[JobUpdate]
    ) -> Job:
        if not self.is_retriable(job=db_obj):
            raise JobNotRetriable()

        # update with params if available
        if retry_input:
            self.update(db, db_obj=db_obj, obj_in=retry_input)

        # mark the job as pending
        self.update_status(db, db_obj=db_obj, status=JobStatus.PENDING)

        return db_obj

    def is_retriable(self, job: Job) -> bool:
        return job.status in retriable_job_statuses

    def is_active(self, job: Job) -> bool:
        return job.status not in terminated_job_statuses

    def can_import(self, job: Job) -> bool:
        return job.status in can_import_job_statuses

    def can_export(self, job: Job) -> bool:
        return job.status in can_export_job_statuses


job = CRUDJob(Job)
