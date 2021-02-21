import uuid

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.crud.base import CRUDBase
from app.models.job import (
    Job,
    JobDuplicated,
    JobNotCancellable,
    JobNotRetriable,
    JobStatus,
    terminated_job_statuses,
)
from app.models.job_log import JobLog
from app.schemas.job import JobCreate


class CRUDJob(CRUDBase[Job, JobCreate]):
    def create(self, db: Session, *, obj_in: JobCreate) -> Job:
        active_job_exists = (
            db.query(Job)
            .filter(
                Job.import_url == obj_in.import_url,
                Job.export_url == obj_in.export_url,
                Job.status in terminated_job_statuses,
            )
            .exists()
            .scalar()
        )
        if active_job_exists:
            raise JobDuplicated()

        db_obj = Job(
            id=uuid.uuid4(),
            import_url=obj_in.import_url,
            import_token=obj_in.import_token,
            export_url=obj_in.export_url,
            export_token=obj_in.export_token,
        )
        # TODO - create folder
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

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

    def cancel(self, db: Session, *, db_obj: Job) -> Job:
        if not self.is_active(job=db_obj):
            raise JobNotCancellable()

        # mark the job as cancelling
        return self.update_status(db, db_obj=db_obj, status=JobStatus.CANCELLING)

    def retry(self, db: Session, *, db_obj: Job) -> Job:
        if self.is_active(job=db_obj):
            raise JobNotRetriable()

        # mark the job as pending
        self.update_status(db, db_obj=db_obj, status=JobStatus.PENDING)
        celery_app.send_task("app.worker.process_job", args=[db_obj])

        return db_obj

    def is_active(self, job: Job) -> bool:
        return job.status not in terminated_job_statuses


job = CRUDJob(Job)
