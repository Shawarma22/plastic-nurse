from typing import Dict, Any
from fastapi import APIRouter, Depends
from app.auth.deps import get_current_user
from app.perception.service import perception_service
from app.services.camera_service import camera_service
from app.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/v1/perception", tags=["perception"])

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
