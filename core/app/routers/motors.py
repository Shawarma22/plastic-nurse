from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.auth.deps import get_current_user
from app.services.motor_service import motor_service

router = APIRouter(prefix="/api/v1/motors", tags=["motors"])

class SpeedRequest(BaseModel):
    speed: float = Field(default=1.0, ge=0.0, le=1.0)

class MotorDriveRequest(BaseModel):
    left_speed: float = Field(default=0.0, ge=-1.0, le=1.0)
    right_speed: float = Field(default=0.0, ge=-1.0, le=1.0)

@router.post("/forward")
async def motor_forward(
    payload: SpeedRequest = SpeedRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.forward(payload.speed)

@router.post("/backward")
async def motor_backward(
    payload: SpeedRequest = SpeedRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.backward(payload.speed)

@router.post("/turn_left")
async def motor_turn_left(
    payload: SpeedRequest = SpeedRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.turn_left(payload.speed)

@router.post("/turn_right")
async def motor_turn_right(
    payload: SpeedRequest = SpeedRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.turn_right(payload.speed)

@router.post("/command")
async def motor_command(
    payload: MotorDriveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.set_motors(payload.left_speed, payload.right_speed)

@router.post("/stop")
async def motor_stop(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return await motor_service.stop()

@router.get("/status")
def motor_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return motor_service.get_status()
