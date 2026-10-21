from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: str = Field(default="operator")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: str = Field(unique=True, index=True)
    patient_ref: str = Field(index=True)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: str = Field(default="active")
    notes: Optional[str] = None

class Vital(SQLModel, table=True):
    __tablename__ = "vitals"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: str = Field(index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    raw_signal: Optional[str] = None
    confidence: Optional[float] = None
    is_calibrated: bool = Field(default=False)
    temperature_ambient: Optional[float] = None
    temperature_object: Optional[float] = None
    temperature_confidence: Optional[float] = None
    target_present: Optional[bool] = None
    lead_off: Optional[bool] = None
    finger_detected: Optional[bool] = None
    current_compartment: Optional[int] = None
    target_compartment: Optional[int] = None
    is_moving: Optional[bool] = None
    is_homed: Optional[bool] = None
    stall_detected: Optional[bool] = None
    battery_mv: Optional[int] = None
    status_flags: Optional[int] = None

class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(index=True)
    payload: Optional[str] = None

class WaveformBatchRecord(SQLModel, table=True):
    __tablename__ = "waveform_batches"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    batch_seq: int = Field(index=True)
    sample_interval_ms: int = Field(default=20)
    sample_count: int = Field(default=32)
    raw_bytes: bytes

class DroidStatusLog(SQLModel, table=True):
    __tablename__ = "droid_status_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(index=True)
    details: Optional[str] = None

class BloodPressureRecord(SQLModel, table=True):
    __tablename__ = "blood_pressure_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    systolic: float = Field(index=True)
    diastolic: float = Field(index=True)
    mean_arterial_pressure: Optional[float] = None
    pulse_rate: Optional[float] = None
    unit: str = Field(default="mmHg")
    device_id: Optional[str] = None
    status_flags: Optional[int] = None
