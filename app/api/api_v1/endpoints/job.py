import uuid
from typing import Any, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.api import deps
from app.core.celery_app import celery_app
from app.models.job import JobDuplicated, JobNotCancellable, JobNotRetriable

router = APIRouter()


@router.post("/", response_model=schemas.Job)
def post_job(
    *, db: Session = Depends(deps.get_db), job_input: schemas.JobCreate
) -> Any:
    try:
        job = crud.job.create(db, obj_in=job_input)
    except JobDuplicated:
        raise HTTPException(
            status_code=requests.codes["conflict"],
            detail="An active job for that (import_url, export_url) already exists",
        )

    celery_app.send_task("app.worker.process_job", args=[job.id])

    return job


@router.get("/{job_id}", response_model=schemas.Job)
def get_job(*, db: Session = Depends(deps.get_db), job_id: uuid.UUID) -> Any:
    job = crud.job.get(db, job_id)
    if not job:
        raise HTTPException(
            status_code=requests.codes["not_found"],
            detail=f"Job with id {job_id} not found",
        )

    return job


@router.post("/{job_id}/retry", response_model=schemas.Job)
def retry(
    *,
    db: Session = Depends(deps.get_db),
    job_id: uuid.UUID,
    retry_input: Optional[schemas.JobUpdate] = None,
) -> Any:
    job = crud.job.get(db, job_id)

    if not job:
        raise HTTPException(
            status_code=requests.codes["not_found"],
            detail=f"Job with id {job_id} not found",
        )

    try:
        crud.job.retry(db, db_obj=job, retry_input=retry_input)
    except JobNotRetriable:
        raise HTTPException(
            status_code=requests.codes["unprocessable"],
            detail="The job can't be retried",
        )

    celery_app.send_task("app.worker.process_job", args=[job.id])

    return job


@router.post("/{job_id}/cancel", response_model=schemas.Job)
def cancel(*, db: Session = Depends(deps.get_db), job_id: uuid.UUID) -> Any:
    job = crud.job.get(db, job_id)
    if not job:
        raise HTTPException(
            status_code=requests.codes["not_found"],
            detail="Job with id {job_id} not found",
        )

    try:
        crud.job.cancel(db, db_obj=job)
    except JobNotCancellable:
        raise HTTPException(
            status_code=requests.codes["unprocessable"],
            detail="The job can't be cancelled",
        )

    return job
