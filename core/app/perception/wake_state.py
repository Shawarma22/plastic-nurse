from enum import Enum
import time
from typing import Dict, Any
from pydantic import BaseModel, Field

class PerceptionLifecycleState(str, Enum):
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    PARSING_INTENT = "parsing_intent"
    EXECUTING_ACTION = "executing_action"
    COOLDOWN = "cooldown"

class LifecycleTransitionEvent(BaseModel):
    previous_state: PerceptionLifecycleState
    new_state: PerceptionLifecycleState
    trigger: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "previous_state": self.previous_state.value,
            "new_state": self.new_state.value,
            "trigger": self.trigger,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
