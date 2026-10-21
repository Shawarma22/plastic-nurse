from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import Vital, WaveformBatchRecord, Event, BloodPressureRecord
from app.auth.deps import get_current_user
from app.services.mqtt_ingest_service import mqtt_ingest_service
from app.services.waveform_parser import WaveformBatchParser
from app.services.ble_bp_service import ble_bp_service
from app.services.alert_engine import alert_engine
from app.services.export_service import export_service

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


class ActiveSessionRequest(BaseModel):
    session_uid: Optional[str] = None


class DispenseCommandRequest(BaseModel):
    cmd: str
    compartment: int = Field(default=0, ge=0, le=13)


class MockBpMeasurementRequest(BaseModel):
    systolic: float = Field(default=120.0, ge=50.0, le=250.0)
    diastolic: float = Field(default=80.0, ge=30.0, le=160.0)
    pulse_rate: float = Field(default=72.0, ge=30.0, le=220.0)
    unit: str = Field(default="mmHg")


@router.get("/status")
def get_telemetry_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    res = mqtt_ingest_service.get_metrics()
    res["mqtt"] = mqtt_ingest_service.get_metrics()
    res["ble_bp"] = ble_bp_service.get_metrics()
    res["alerts"] = alert_engine.get_metrics()
    return res


@router.post("/session")
def set_active_session(
    payload: ActiveSessionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    mqtt_ingest_service.set_active_session_uid(payload.session_uid)
    ble_bp_service.set_active_session_uid(payload.session_uid)
    alert_engine.set_active_session_uid(payload.session_uid)
    return {"status": "ok", "active_session_uid": payload.session_uid}


@router.post("/session/{session_uid}")
def set_active_session_path(
    session_uid: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    uid = None if session_uid == "none" or not session_uid else session_uid
    mqtt_ingest_service.set_active_session_uid(uid)
    ble_bp_service.set_active_session_uid(uid)
    alert_engine.set_active_session_uid(uid)
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


@router.get("/bp/status")
def get_ble_bp_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    return ble_bp_service.get_metrics()


@router.get("/bp/latest")
def get_latest_blood_pressure(
    session_uid: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Optional[Dict[str, Any]]:
    query = select(BloodPressureRecord)
    target_uid = session_uid or ble_bp_service.active_session_uid
    if target_uid:
        query = query.where(BloodPressureRecord.session_uid == target_uid)
    query = query.order_by(BloodPressureRecord.timestamp.desc())
    record = db.exec(query).first()
    if not record:
        return None
    return record.model_dump()


@router.post("/bp/mock-measure")
def trigger_mock_bp_measurement(
    payload: MockBpMeasurementRequest = MockBpMeasurementRequest(),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    record = ble_bp_service.trigger_mock_measurement(
        systolic=payload.systolic,
        diastolic=payload.diastolic,
        pulse_rate=payload.pulse_rate,
        unit=payload.unit,
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process blood pressure measurement",
        )
    return record


@router.get("/alerts/recent")
def get_recent_alerts(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return alert_engine.get_recent_alerts(limit=limit)


@router.get("/export/json/{session_uid}")
def export_session_json(
    session_uid: str,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    data = export_service.export_json(session_uid, db)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or has no recorded telemetry",
        )
    return data


@router.get("/export/csv/{session_uid}")
def export_session_csv(
    session_uid: str,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    csv_str = export_service.export_csv(session_uid, db)
    if not csv_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or has no recorded telemetry",
        )
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="telemetry_{session_uid}.csv"'},
    )


@router.get("/export/report/{session_uid}")
def export_session_report(
    session_uid: str,
    db: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    rep_str = export_service.export_summary_report(session_uid, db)
    if not rep_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or has no recorded telemetry",
        )
    return Response(
        content=rep_str,
        media_type="text/plain",
    )
