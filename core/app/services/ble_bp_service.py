import asyncio
import queue
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlmodel import Session
from app.config import settings
from app.logger import logger
from app.db.session import engine
from app.db.models import BloodPressureRecord
from app.services.ble_bp_parser import BleBloodPressureParser
from app.services.ws_manager import ws_manager

try:
    import bleak
except ImportError:
    bleak = None


class BleConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"


class BleBloodPressureService:
    def __init__(self) -> None:
        self.state = BleConnectionState.DISCONNECTED
        self.connected_device_name: Optional[str] = None
        self.connected_device_address: Optional[str] = None
        self.last_measurement_time: Optional[datetime] = None
        self.active_session_uid: Optional[str] = None
        self.received_measurements_count = 0
        self.persisted_measurements_count = 0
        self.measurement_queue: queue.Queue = queue.Queue(maxsize=200)
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._persistence_thread: Optional[threading.Thread] = None
        self.mock_mode = (settings.DROID_HAL == "mock") or (bleak is None)
        self.last_measurement: Optional[Dict[str, Any]] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def get_state(self) -> str:
        return self.state.value

    def is_connected(self) -> bool:
        return self.state == BleConnectionState.CONNECTED

    def set_active_session_uid(self, uid: Optional[str]) -> None:
        self.active_session_uid = uid

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def _broadcast_telemetry(self, data: Dict[str, Any]) -> None:
        if self.loop and self.loop.is_running():
            try:
                payload = {
                    "type": "blood_pressure",
                    "data": {
                        "session_uid": data.get("session_uid"),
                        "timestamp": data["timestamp"].isoformat() if isinstance(data["timestamp"], datetime) else str(data["timestamp"]),
                        "systolic": data["systolic"],
                        "diastolic": data["diastolic"],
                        "mean_arterial_pressure": data.get("mean_arterial_pressure"),
                        "pulse_rate": data.get("pulse_rate"),
                        "unit": data.get("unit", "mmHg"),
                        "device_id": data.get("device_id"),
                    },
                }
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_telemetry(payload),
                    self.loop,
                )
            except Exception as exc:
                logger.debug(f"Failed to bridge ble bp to websocket: {exc}")

    def _broadcast_state(self, state: str) -> None:
        if self.loop and self.loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_state({"ble_bp": state, "device": self.connected_device_name}),
                    self.loop,
                )
            except Exception:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "is_connected": self.is_connected(),
            "mock_mode": self.mock_mode,
            "connected_device_name": self.connected_device_name,
            "connected_device_address": self.connected_device_address,
            "last_measurement_time": self.last_measurement_time.isoformat() if self.last_measurement_time else None,
            "received_measurements_count": self.received_measurements_count,
            "persisted_measurements_count": self.persisted_measurements_count,
            "queue_size": self.measurement_queue.qsize(),
            "active_session_uid": self.active_session_uid,
        }

    def handle_raw_measurement_bytes(self, data: bytes, device_id: str = "mock-device") -> Optional[Dict[str, Any]]:
        parsed = BleBloodPressureParser.unpack(data)
        if not parsed:
            return None
        record_data = {
            "session_uid": self.active_session_uid,
            "timestamp": parsed["timestamp"],
            "systolic": parsed["systolic"],
            "diastolic": parsed["diastolic"],
            "mean_arterial_pressure": parsed["mean_arterial_pressure"],
            "pulse_rate": parsed["pulse_rate"],
            "unit": parsed["unit"],
            "device_id": device_id,
            "status_flags": parsed["status_flags"],
        }
        self.received_measurements_count += 1
        self.last_measurement_time = datetime.now(timezone.utc)
        self.last_measurement = record_data
        try:
            self.measurement_queue.put_nowait(record_data)
        except queue.Full:
            try:
                self.measurement_queue.get_nowait()
                self.measurement_queue.put_nowait(record_data)
            except Exception:
                pass
        self._broadcast_telemetry(record_data)
        return record_data

    def flush_measurements_batch(self, limit: int = 25) -> int:
        batch: List[Dict[str, Any]] = []
        for _ in range(limit):
            try:
                item = self.measurement_queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break
        if not batch:
            return 0
        try:
            with Session(engine) as session:
                for item in batch:
                    record = BloodPressureRecord(
                        session_uid=item.get("session_uid") or self.active_session_uid,
                        timestamp=item.get("timestamp", datetime.now(timezone.utc)),
                        systolic=item["systolic"],
                        diastolic=item["diastolic"],
                        mean_arterial_pressure=item.get("mean_arterial_pressure"),
                        pulse_rate=item.get("pulse_rate"),
                        unit=item.get("unit", "mmHg"),
                        device_id=item.get("device_id"),
                        status_flags=item.get("status_flags"),
                    )
                    session.add(record)
                session.commit()
            self.persisted_measurements_count += len(batch)
            return len(batch)
        except Exception as exc:
            logger.warning(f"Error persisting blood pressure batch: {exc}")
            return 0

    def trigger_mock_measurement(
        self,
        systolic: float = 120.0,
        diastolic: float = 80.0,
        pulse_rate: float = 72.0,
        unit: str = "mmHg",
    ) -> Optional[Dict[str, Any]]:
        mean_ap = round((2.0 * diastolic + systolic) / 3.0, 1)
        data = BleBloodPressureParser.pack(
            systolic=systolic,
            diastolic=diastolic,
            mean_arterial_pressure=mean_ap,
            pulse_rate=pulse_rate,
            unit=unit,
            dt=datetime.now(timezone.utc),
        )
        return self.handle_raw_measurement_bytes(data, device_id="BP_MOCK_ARM_01")

    def _mock_scanner_worker(self) -> None:
        self.state = BleConnectionState.SCANNING
        self._broadcast_state("scanning")
        time.sleep(0.5)
        self.state = BleConnectionState.CONNECTING
        self._broadcast_state("connecting")
        time.sleep(0.5)
        self.state = BleConnectionState.CONNECTED
        self.connected_device_name = "BP_MOCK_ARM_01"
        self.connected_device_address = "AA:BB:CC:11:22:33"
        self._broadcast_state("connected")
        logger.info(f"Mock BLE Blood Pressure monitor connected: {self.connected_device_name}")

        while self.running:
            time.sleep(1.0)

        self.state = BleConnectionState.DISCONNECTED
        self.connected_device_name = None
        self.connected_device_address = None
        self._broadcast_state("disconnected")

    def _persistence_worker(self) -> None:
        while self.running:
            try:
                self.flush_measurements_batch(25)
            except Exception as exc:
                logger.warning(f"Unexpected error in ble bp persistence worker: {exc}")
            time.sleep(1.0)
        try:
            self.flush_measurements_batch(100)
        except Exception:
            pass

    def start(self) -> None:
        if self.running or not settings.BLE_BP_ENABLED:
            return
        self.running = True
        self._thread = threading.Thread(target=self._mock_scanner_worker, daemon=True)
        self._thread.start()
        self._persistence_thread = threading.Thread(target=self._persistence_worker, daemon=True)
        self._persistence_thread.start()

    def stop(self) -> None:
        self.running = False
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass
        self._thread = None
        if self._persistence_thread and self._persistence_thread.is_alive():
            try:
                self._persistence_thread.join(timeout=2.0)
            except Exception:
                pass
        self._persistence_thread = None
        self.state = BleConnectionState.DISCONNECTED
        self.connected_device_name = None
        self.connected_device_address = None
        self._broadcast_state("disconnected")


ble_bp_service = BleBloodPressureService()
