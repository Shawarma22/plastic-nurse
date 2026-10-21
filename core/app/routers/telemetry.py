from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import Vital, WaveformBatchRecord, Event
from app.auth.deps import get_current_user
from app.services.mqtt_ingest_service import mqtt_ingest_service
from app.services.waveform_parser import WaveformBatchParser

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


class ActiveSessionRequest(BaseModel):
    session_uid: Optional[str] = None


class DispenseCommandRequest(BaseModel):
    cmd: str
    compartment: int = Field(default=0, ge=0, le=13)


@router.get("/status")
def get_telemetry_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return mqtt_ingest_service.get_metrics()


@router.post("/session")
def set_active_session(
    payload: ActiveSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    mqtt_ingest_service.set_active_session_uid(payload.session_uid)
    return {"status": "ok", "active_session_uid": payload.session_uid}


@router.post("/session/{session_uid}")
def set_active_session_path(
    session_uid: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    uid = None if session_uid == "none" or not session_uid else session_uid
    mqtt_ingest_service.set_active_session_uid(uid)
    return {"status": "ok", "active_session_uid": uid}


@router.get("/vitals/latest")
def get_latest_vitals(
    session_uid: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Optional[Dict[str, Any]]:
    query = select(Vital)
    target_uid = session_uid or mqtt_ingest_service.active_session_uid
    if target_uid:
        query = query.where(Vital.session_uid == target_uid)
    query = query.order_by(Vital.timestamp.desc())
    record = db.exec(query).first()
    if not record:
        return None
    return record.model_dump()


@router.get("/waveforms/latest")
def get_latest_waveform(
    session_uid: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Optional[Dict[str, Any]]:
    query = select(WaveformBatchRecord)
    target_uid = session_uid or mqtt_ingest_service.active_session_uid
    if target_uid:
        query = query.where(WaveformBatchRecord.session_uid == target_uid)
    query = query.order_by(WaveformBatchRecord.timestamp.desc())
    record = db.exec(query).first()
    if not record:
        return None
    unpacked = WaveformBatchParser.unpack(record.raw_bytes)
    return {
        "id": record.id,
        "session_uid": record.session_uid,
        "timestamp": record.timestamp.isoformat(),
        "batch_seq": record.batch_seq,
        "unpacked": unpacked,
    }


@router.post("/dispense")
def send_dispense_command(
    payload: DispenseCommandRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    success = mqtt_ingest_service.publish_dispense_command(payload.cmd, payload.compartment)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to publish dispense command or client disconnected",
        )
    return {"status": "dispatched", "cmd": payload.cmd, "compartment": payload.compartment}


@router.get("/events/latest")
def get_latest_events(
    limit: int = 20,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    records = db.exec(select(Event).order_by(Event.timestamp.desc()).limit(limit)).all()
    return [r.model_dump() for r in records]
