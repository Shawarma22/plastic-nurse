from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class StepType(str, Enum):
    PROMPT = "prompt"
    WAIT = "wait"
    MEASURE = "measure"
    BRANCH = "branch"
    DISPENSE = "dispense"
    FINISH = "finish"


class ProtocolState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


class BranchCondition(BaseModel):
    variable: str
    operator: str
    value: Any
    target_step: str


class StepDefinition(BaseModel):
    id: str
    type: StepType
    text: Optional[str] = None
    duration_sec: Optional[float] = None
    target_vital: Optional[str] = None
    timeout_sec: Optional[float] = None
    conditions: Optional[List[BranchCondition]] = None
    default_next: Optional[str] = None
    item_id: Optional[str] = None


class ProtocolMetadata(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    estimated_duration_sec: Optional[int] = None


class ProtocolSchema(BaseModel):
    metadata: ProtocolMetadata
    initial_step: str
    steps: List[StepDefinition] = Field(default_factory=list)
