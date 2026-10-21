import asyncio
import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlmodel import Session
from app.config import settings
from app.logger import logger
from app.db.session import engine
from app.db.models import Event
from app.services.ws_manager import ws_manager


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

    def _dispatch_alert(self, alert: Dict[str, Any]) -> None:
        if self.loop and self.loop.is_running():
            try:
                payload = {
                    "type": "telemetry_alert",
                    "alert": alert,
                }
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_telemetry(payload),
                    self.loop,
                )
            except Exception as exc:
                logger.debug(f"Failed to broadcast alert to websocket: {exc}")
        try:
            with Session(engine) as session:
                record = Event(
                    session_uid=alert.get("session_uid"),
                    timestamp=datetime.now(timezone.utc),
                    event_type="telemetry_alert",
                    payload=json.dumps(alert),
                )
                session.add(record)
                session.commit()
        except Exception as exc:
            logger.debug(f"Failed to persist alert event to database: {exc}")

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
        self._dispatch_alert(alert)
        return alert

    def evaluate_vitals(self, vital: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(vital, dict):
            return []
        alerts: List[Dict[str, Any]] = []
        conf = vital.get("confidence")
        conf_ok = conf is None or conf >= settings.ALERT_CONFIDENCE_THRESHOLD
        finger = vital.get("finger_detected", True)
        hr = vital.get("heart_rate")

        if conf_ok and finger and hr is not None and hr > 0:
            if hr > settings.ALERT_HEART_RATE_MAX and not self._is_cooling_down("heart_rate_high"):
                sev = "critical" if hr > 160.0 else "warning"
                msg = f"Observed heart rate of {hr:.1f} bpm exceeds upper threshold bound of {settings.ALERT_HEART_RATE_MAX:.1f} bpm"
                alerts.append(self.create_alert("heart_rate_high", hr, settings.ALERT_HEART_RATE_MAX, sev, msg, vital.get("session_uid")))
            elif hr < settings.ALERT_HEART_RATE_MIN and not self._is_cooling_down("heart_rate_low"):
                sev = "critical" if hr < 35.0 else "warning"
                msg = f"Observed heart rate of {hr:.1f} bpm is below lower threshold bound of {settings.ALERT_HEART_RATE_MIN:.1f} bpm"
                alerts.append(self.create_alert("heart_rate_low", hr, settings.ALERT_HEART_RATE_MIN, sev, msg, vital.get("session_uid")))

        spo2 = vital.get("spo2")
        if conf_ok and finger and spo2 is not None and spo2 > 0:
            if spo2 < settings.ALERT_SPO2_MIN and not self._is_cooling_down("spo2_low"):
                sev = "critical" if spo2 < 85.0 else "warning"
                msg = f"Observed oxygen saturation of {spo2:.1f}% is below threshold bound of {settings.ALERT_SPO2_MIN:.1f}%"
                alerts.append(self.create_alert("spo2_low", spo2, settings.ALERT_SPO2_MIN, sev, msg, vital.get("session_uid")))

        temp_obj = vital.get("temperature_object")
        target_pres = vital.get("target_present", True)
        if target_pres and temp_obj is not None:
            if temp_obj > settings.ALERT_TEMP_OBJECT_MAX_C and not self._is_cooling_down("temp_obj_high"):
                sev = "critical" if temp_obj > 39.5 else "warning"
                msg = f"Observed object temperature of {temp_obj:.1f} C exceeds upper threshold bound of {settings.ALERT_TEMP_OBJECT_MAX_C:.1f} C"
                alerts.append(self.create_alert("temp_obj_high", temp_obj, settings.ALERT_TEMP_OBJECT_MAX_C, sev, msg, vital.get("session_uid")))
            elif temp_obj < settings.ALERT_TEMP_OBJECT_MIN_C and temp_obj > 25.0 and not self._is_cooling_down("temp_obj_low"):
                msg = f"Observed object temperature of {temp_obj:.1f} C is below lower threshold bound of {settings.ALERT_TEMP_OBJECT_MIN_C:.1f} C"
                alerts.append(self.create_alert("temp_obj_low", temp_obj, settings.ALERT_TEMP_OBJECT_MIN_C, "warning", msg, vital.get("session_uid")))

        if vital.get("stall_detected") and not self._is_cooling_down("carousel_stall"):
            comp = vital.get("current_compartment", 0)
            msg = f"Carousel motor stall detected at compartment {comp}"
            alerts.append(self.create_alert("carousel_stall", True, False, "critical", msg, vital.get("session_uid")))

        return alerts

    def evaluate_blood_pressure(self, bp: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(bp, dict):
            return []
        alerts: List[Dict[str, Any]] = []
        sys_val = bp.get("systolic")
        dia_val = bp.get("diastolic")
        unit = bp.get("unit", "mmHg")

        if sys_val is not None:
            if sys_val > settings.ALERT_BP_SYSTOLIC_MAX and not self._is_cooling_down("bp_systolic_high"):
                sev = "critical" if sys_val > 180.0 else "warning"
                msg = f"Observed systolic pressure of {sys_val:.1f} {unit} exceeds threshold bound of {settings.ALERT_BP_SYSTOLIC_MAX:.1f} {unit}"
                alerts.append(self.create_alert("bp_systolic_high", sys_val, settings.ALERT_BP_SYSTOLIC_MAX, sev, msg, bp.get("session_uid")))
            elif sys_val < settings.ALERT_BP_SYSTOLIC_MIN and sys_val > 40.0 and not self._is_cooling_down("bp_systolic_low"):
                sev = "critical" if sys_val < 70.0 else "warning"
                msg = f"Observed systolic pressure of {sys_val:.1f} {unit} is below threshold bound of {settings.ALERT_BP_SYSTOLIC_MIN:.1f} {unit}"
                alerts.append(self.create_alert("bp_systolic_low", sys_val, settings.ALERT_BP_SYSTOLIC_MIN, sev, msg, bp.get("session_uid")))

        if dia_val is not None:
            if dia_val > settings.ALERT_BP_DIASTOLIC_MAX and not self._is_cooling_down("bp_diastolic_high"):
                sev = "critical" if dia_val > 120.0 else "warning"
                msg = f"Observed diastolic pressure of {dia_val:.1f} {unit} exceeds threshold bound of {settings.ALERT_BP_DIASTOLIC_MAX:.1f} {unit}"
                alerts.append(self.create_alert("bp_diastolic_high", dia_val, settings.ALERT_BP_DIASTOLIC_MAX, sev, msg, bp.get("session_uid")))
            elif dia_val < settings.ALERT_BP_DIASTOLIC_MIN and dia_val > 20.0 and not self._is_cooling_down("bp_diastolic_low"):
                msg = f"Observed diastolic pressure of {dia_val:.1f} {unit} is below threshold bound of {settings.ALERT_BP_DIASTOLIC_MIN:.1f} {unit}"
                alerts.append(self.create_alert("bp_diastolic_low", dia_val, settings.ALERT_BP_DIASTOLIC_MIN, "warning", msg, bp.get("session_uid")))

        return alerts

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
