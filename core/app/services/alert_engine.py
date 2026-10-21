import asyncio
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.config import settings
from app.logger import logger


class TelemetryAlertEngine:
    def __init__(self) -> None:
        self.active_session_uid: Optional[str] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.cooldown_sec = settings.ALERT_COOLDOWN_SEC
        self._last_alert_timestamps: Dict[str, float] = {}
        self._alerts_history: deque = deque(maxlen=200)
        self.total_alerts_count = 0

    def set_active_session_uid(self, uid: Optional[str]) -> None:
        self.active_session_uid = uid

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def _is_cooling_down(self, parameter: str) -> bool:
        now = time.time()
        last = self._last_alert_timestamps.get(parameter, 0.0)
        return (now - last) < self.cooldown_sec

    def _record_cooldown(self, parameter: str) -> None:
        self._last_alert_timestamps[parameter] = time.time()

    def create_alert(
        self,
        parameter: str,
        observed_value: Any,
        threshold_bound: Any,
        severity: str,
        message: str,
        session_uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        alert = {
            "alert_id": str(uuid.uuid4()),
            "session_uid": session_uid or self.active_session_uid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameter": parameter,
            "observed_value": observed_value,
            "threshold_bound": threshold_bound,
            "severity": severity,
            "message": message,
        }
        self._record_cooldown(parameter)
        self._alerts_history.append(alert)
        self.total_alerts_count += 1
        logger.warning(f"Telemetry threshold alert: {message}")
        return alert

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        items = list(self._alerts_history)
        return items[-limit:] if limit > 0 else items

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "total_alerts_count": self.total_alerts_count,
            "active_session_uid": self.active_session_uid,
            "history_size": len(self._alerts_history),
            "cooldown_sec": self.cooldown_sec,
            "recent_alert": self._alerts_history[-1] if self._alerts_history else None,
        }


alert_engine = TelemetryAlertEngine()
