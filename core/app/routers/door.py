from typing import Dict, Any
from fastapi import APIRouter, Depends
from app.auth.deps import get_current_user
from app.services.door_service import door_service

router = APIRouter(prefix="/api/v1/door", tags=["door"])

@router.post("/open")
async def open_door(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await door_service.open_door()

@router.post("/close")
async def close_door(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await door_service.close_door()

@router.post("/stop")
async def stop_door(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await door_service.stop()

@router.get("/status")
def door_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return door_service.get_status()
