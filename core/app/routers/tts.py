from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.auth.deps import get_current_user
from app.services.tts_service import tts_service

router = APIRouter(prefix="/api/v1/tts", tags=["tts"])


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    engine: Optional[str] = None


class CancelRequest(BaseModel):
    utterance_id: Optional[str] = None


@router.get("/status")
def get_tts_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return tts_service.get_metrics()
