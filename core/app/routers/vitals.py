import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import Session as DBSession, Vital, Event
from app.auth.deps import get_current_user
from app.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/v1/vitals", tags=["vitals"])

class SessionCreate(BaseModel):
    patient_ref: str
    notes: Optional[str] = None

class SessionResponse(BaseModel):
    id: int
    session_uid: str
    patient_ref: str
    status: str
    notes: Optional[str]

class VitalCreate(BaseModel):
    session_uid: str
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    raw_signal: Optional[str] = None
    confidence: Optional[float] = None
    is_calibrated: bool = False

class VitalResponse(BaseModel):
    id: int
    session_uid: str
    heart_rate: Optional[float]
    spo2: Optional[float]
    confidence: Optional[float]
    is_calibrated: bool

class EventCreate(BaseModel):
    session_uid: Optional[str] = None
    event_type: str
    payload: Optional[str] = None

class EventResponse(BaseModel):
    id: int
    session_uid: Optional[str]
    event_type: str
    payload: Optional[str]

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> SessionResponse:
    uid = str(uuid.uuid4())
    db_session = DBSession(
        session_uid=uid,
        patient_ref=payload.patient_ref,
        notes=payload.notes,
        status="active"
    )
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return SessionResponse(
        id=db_session.id or 0,
        session_uid=db_session.session_uid,
        patient_ref=db_session.patient_ref,
        status=db_session.status,
        notes=db_session.notes
    )

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[SessionResponse]:
    sessions = session.exec(select(DBSession).order_by(DBSession.start_time.desc())).all()
    return [
        SessionResponse(
            id=s.id or 0,
            session_uid=s.session_uid,
            patient_ref=s.patient_ref,
            status=s.status,
            notes=s.notes
        )
        for s in sessions
    ]

@router.post("/records", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
async def record_vitals(
    payload: VitalCreate,
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> VitalResponse:
    vital = Vital(
        session_uid=payload.session_uid,
        heart_rate=payload.heart_rate,
        spo2=payload.spo2,
        raw_signal=payload.raw_signal,
        confidence=payload.confidence,
        is_calibrated=payload.is_calibrated
    )
    session.add(vital)
    session.commit()
    session.refresh(vital)

    await ws_manager.broadcast_telemetry({
        "type": "vital_reading",
        "session_uid": vital.session_uid,
        "heart_rate": vital.heart_rate,
        "spo2": vital.spo2,
        "confidence": vital.confidence,
        "is_calibrated": vital.is_calibrated
    })

    return VitalResponse(
        id=vital.id or 0,
        session_uid=vital.session_uid,
        heart_rate=vital.heart_rate,
        spo2=vital.spo2,
        confidence=vital.confidence,
        is_calibrated=vital.is_calibrated
    )

@router.get("/records/{session_uid}", response_model=List[VitalResponse])
def get_vitals_by_session(
    session_uid: str,
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[VitalResponse]:
    records = session.exec(select(Vital).where(Vital.session_uid == session_uid)).all()
    return [
        VitalResponse(
            id=r.id or 0,
            session_uid=r.session_uid,
            heart_rate=r.heart_rate,
            spo2=r.spo2,
            confidence=r.confidence,
            is_calibrated=r.is_calibrated
        )
        for r in records
    ]

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def record_event(
    payload: EventCreate,
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> EventResponse:
    event = Event(
        session_uid=payload.session_uid,
        event_type=payload.event_type,
        payload=payload.payload
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    await ws_manager.broadcast_state({
        "type": "system_event",
        "event_type": event.event_type,
        "session_uid": event.session_uid,
        "payload": event.payload
    })

    return EventResponse(
        id=event.id or 0,
        session_uid=event.session_uid,
        event_type=event.event_type,
        payload=event.payload
    )

@router.get("/events/{session_uid}", response_model=List[EventResponse])
def get_events_by_session(
    session_uid: str,
    session: Session = Depends(get_session),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[EventResponse]:
    events = session.exec(select(Event).where(Event.session_uid == session_uid)).all()
    return [
        EventResponse(
            id=e.id or 0,
            session_uid=e.session_uid,
            event_type=e.event_type,
            payload=e.payload
        )
        for e in events
    ]
