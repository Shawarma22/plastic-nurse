from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from app.schemas.protocol import ProtocolState


class ProtocolExecutionContext:
    def __init__(
        self,
        protocol_id: str,
        session_uid: Optional[str] = None,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.execution_id: str = str(uuid.uuid4())
        self.protocol_id: str = protocol_id
        self.session_uid: str = session_uid or f"proto-sess-{self.execution_id[:8]}"
        self.current_step_id: Optional[str] = None
        self.state: ProtocolState = ProtocolState.IDLE
        self.variables: Dict[str, Any] = dict(initial_variables or {})
        self.step_history: List[Dict[str, Any]] = []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None

    def set_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set_state(self, new_state: ProtocolState) -> None:
        self.state = new_state
        if new_state == ProtocolState.RUNNING and self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        elif new_state in (ProtocolState.COMPLETED, ProtocolState.ABORTED, ProtocolState.ERROR):
            self.completed_at = datetime.now(timezone.utc)

    def record_step(self, step_id: str, step_type: str, result: Optional[Dict[str, Any]] = None) -> None:
        entry = {
            "step_id": step_id,
            "step_type": step_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": result or {},
        }
        self.step_history.append(entry)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "protocol_id": self.protocol_id,
            "session_uid": self.session_uid,
            "current_step_id": self.current_step_id,
            "state": self.state.value,
            "variables": dict(self.variables),
            "step_count": len(self.step_history),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
