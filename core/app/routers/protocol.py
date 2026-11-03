from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.auth.deps import get_current_user
from app.services.protocol_engine import protocol_engine

router = APIRouter(prefix="/api/v1/protocols", tags=["protocols"])


class StartProtocolRequest(BaseModel):
    protocol_id: str = Field(..., min_length=1)
    session_uid: Optional[str] = None
    initial_vars: Optional[Dict[str, Any]] = None


class AbortProtocolRequest(BaseModel):
    reason: Optional[str] = None


@router.get("")
def list_protocols(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    return protocol_engine.list_protocols()


@router.get("/status")
def get_protocol_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    return protocol_engine.get_status()


@router.get("/{protocol_id}")
def get_protocol_definition(
    protocol_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    proto = protocol_engine.get_protocol(protocol_id)
    if not proto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Protocol '{protocol_id}' not found",
        )
    return proto.model_dump()


@router.post("/start")
async def start_protocol(
    request: StartProtocolRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        ctx = await protocol_engine.start_protocol(
            protocol_id=request.protocol_id,
            session_uid=request.session_uid,
            initial_vars=request.initial_vars,
        )
        return ctx.snapshot()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/pause")
async def pause_protocol(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    success = await protocol_engine.pause_protocol()
    return {"success": success, "status": protocol_engine.get_status()}


@router.post("/resume")
async def resume_protocol(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    success = await protocol_engine.resume_protocol()
    return {"success": success, "status": protocol_engine.get_status()}


@router.post("/abort")
async def abort_protocol(
    request: Optional[AbortProtocolRequest] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    reason = request.reason if request else None
    success = await protocol_engine.abort_protocol(reason)
    return {"success": success, "status": protocol_engine.get_status()}
