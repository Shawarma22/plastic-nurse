from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Response
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


@router.post("/speak")
def speak_text(
    request: SpeakRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    utterance_id = tts_service.enqueue_speech(request.text, request.engine)
    return {
        "utterance_id": utterance_id,
        "status": "queued",
        "text": request.text,
        "engine": request.engine or tts_service.engine_type,
    }


@router.post("/synthesize")
def direct_synthesize(
    request: SpeakRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Response:
    audio_bytes, used_engine = tts_service.synthesize(request.text, request.engine)
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"X-TTS-Engine": used_engine},
    )


@router.post("/cancel")
def cancel_playback(
    request: CancelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    if request.utterance_id:
        cancelled = tts_service.cancel_utterance(request.utterance_id)
        return {"cancelled": cancelled, "utterance_id": request.utterance_id}
    tts_service.stop()
    return {"cancelled": True, "action": "stopped_all"}


@router.post("/stop")
def stop_playback(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    tts_service.stop()
    return {"status": "stopped"}


@router.delete("/cache")
def clear_tts_cache(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    cleared = tts_service.clear_cache()
    return {"cleared_files": cleared}
