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

class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_uid: Optional[str] = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(index=True)
    payload: Optional[str] = None
