from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth.deps import get_current_user
from app.services.job_queue import job_queue_service

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

class JobSubmitRequest(BaseModel):
    job_type: str
    payload: Optional[Dict[str, Any]] = None

@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(
    request: JobSubmitRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    job = await job_queue_service.submit_job(
        job_type=request.job_type,
        payload=request.payload
    )
    return job.to_dict()

@router.get("/{job_id}")
def get_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    job = job_queue_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job.to_dict()
