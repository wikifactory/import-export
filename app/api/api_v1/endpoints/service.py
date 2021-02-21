from fastapi import APIRouter, Depends, HTTPException

from app import schemas

router = APIRouter()


@router.post("/validate", response_model=schemas.Service)
def validate_url(*, url: schemas.Service):
    # check against available urls, return valid service
    return ""
