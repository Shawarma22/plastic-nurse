import base64
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.deps import get_current_user
from app.perception.service import perception_service
from app.perception.stt import VoskSpeechRecognizer
from app.perception.audio import MockAudioSource
from app.services.camera_service import camera_service
from app.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/v1/perception", tags=["perception"])

stt_recognizer = VoskSpeechRecognizer()
audio_source = MockAudioSource()

class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None
    simulate_phrase: Optional[str] = None

@router.get("/status")
def get_perception_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return perception_service.get_status().to_dict()

@router.post("/analyze")
async def analyze_current_frame(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    frame = camera_service.get_latest_frame()
    state = perception_service.process_frame(frame)
    payload = state.to_dict()
    await ws_manager.broadcast_state({
        "type": "perception_update",
        "perception": payload
    })
    return payload

@router.post("/stt/transcribe")
async def transcribe_audio_chunk(
    request: TranscribeRequest = TranscribeRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    if request.simulate_phrase:
        return {
            "transcript": request.simulate_phrase,
            "is_final": True,
            "confidence": 0.95
        }
    if request.audio_base64:
        raw_pcm = base64.b64decode(request.audio_base64)
    else:
        audio_source.start()
        raw_pcm = audio_source.read_chunk(8192)
        audio_source.stop()
    res = stt_recognizer.accept_waveform(raw_pcm)
    if not res:
        res = stt_recognizer.get_final_result()
    payload = {
        "transcript": res.transcript,
        "is_final": res.is_final,
        "confidence": res.confidence
    }
    if res.transcript:
        await ws_manager.broadcast_state({
            "type": "voice_transcript",
            "transcript": res.transcript,
            "is_final": res.is_final
        })
    return payload
