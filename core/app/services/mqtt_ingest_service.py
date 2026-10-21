import json
import queue
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
import paho.mqtt.client as mqtt
from sqlmodel import Session
from app.config import settings
from app.logger import logger
from app.db.session import engine
from app.db.models import DroidStatusLog, Vital


class MqttConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MqttIngestService:
    def __init__(
        self,
        broker: str = settings.MQTT_BROKER_HOST,
        port: int = settings.MQTT_BROKER_PORT,
        client_id: str = settings.MQTT_CLIENT_ID,
    ) -> None:
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.state = MqttConnectionState.DISCONNECTED
        self.droid_online = False
        self.last_status_time: Optional[datetime] = None
        self.last_telemetry_time: Optional[datetime] = None
        self.received_packets_count = 0
        self.received_batches_count = 0
        self.received_events_count = 0
        self.persisted_vitals_count = 0
        self.active_session_uid: Optional[str] = None
        self.client: Optional[mqtt.Client] = None
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self.vitals_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.waveform_queue: queue.Queue = queue.Queue(maxsize=500)
        self.events_queue: queue.Queue = queue.Queue(maxsize=500)

    def is_connected(self) -> bool:
        return self.state == MqttConnectionState.CONNECTED

    def is_droid_online(self) -> bool:
        return self.droid_online

    def get_state(self) -> str:
        return self.state.value

    def set_active_session_uid(self, uid: Optional[str]) -> None:
        self.active_session_uid = uid

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "droid_online": self.droid_online,
            "broker": f"{self.broker}:{self.port}",
            "client_id": self.client_id,
            "active_session_uid": self.active_session_uid,
            "last_status_time": self.last_status_time.isoformat() if self.last_status_time else None,
            "last_telemetry_time": self.last_telemetry_time.isoformat() if self.last_telemetry_time else None,
            "received_packets_count": self.received_packets_count,
            "received_batches_count": self.received_batches_count,
            "received_events_count": self.received_events_count,
            "persisted_vitals_count": self.persisted_vitals_count,
            "vitals_queue_size": self.vitals_queue.qsize(),
            "waveform_queue_size": self.waveform_queue.qsize(),
            "events_queue_size": self.events_queue.qsize(),
        }

    def _init_client(self) -> None:
        if hasattr(mqtt, "CallbackAPIVersion"):
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
            )
        else:
            self.client = mqtt.Client(
                client_id=self.client_id,
                protocol=mqtt.MQTTv311,
            )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: Any, rc: Any, *args: Any, **kwargs: Any
    ) -> None:
        code = getattr(rc, "value", rc)
        if code == 0:
            self.state = MqttConnectionState.CONNECTED
            logger.info(f"MQTT subscriber connected to {self.broker}:{self.port}")
            self._subscribe_topics()
        else:
            self.state = MqttConnectionState.FAILED
            logger.warning(f"MQTT subscriber connect failed with code {code}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, *args: Any, **kwargs: Any) -> None:
        if self.running:
            self.state = MqttConnectionState.RECONNECTING
        else:
            self.state = MqttConnectionState.DISCONNECTED
        self.droid_online = False
        logger.info("MQTT subscriber disconnected")

    def _subscribe_topics(self) -> None:
        if not self.client:
            return
        topics = [
            (settings.MQTT_TOPIC_STATUS, 1),
            (settings.MQTT_TOPIC_VITALS_PROCESSED, 0),
            (settings.MQTT_TOPIC_VITALS_RAW, 0),
            (settings.MQTT_TOPIC_VITALS_EVENTS, 0),
        ]
        self.client.subscribe(topics)

    def _handle_status_message(self, payload: str) -> None:
        self.droid_online = payload.lower() == "online"
        self.last_status_time = datetime.now(timezone.utc)
        logger.info(f"Droid status updated: {payload}")
        self._log_status_to_db(payload)

    def _log_status_to_db(self, status: str) -> None:
        try:
            with Session(engine) as session:
                log_entry = DroidStatusLog(
                    timestamp=datetime.now(timezone.utc),
                    status=status,
                    details=f"Received via {settings.MQTT_TOPIC_STATUS}",
                )
                session.add(log_entry)
                session.commit()
        except Exception as exc:
            logger.warning(f"Failed to record droid status log: {exc}")

    @staticmethod
    def parse_vitals_payload(payload_bytes: bytes) -> Optional[Dict[str, Any]]:
        try:
            raw_str = payload_bytes.decode("utf-8", errors="ignore").strip()
            data = json.loads(raw_str)
            if not isinstance(data, dict):
                return None
            ppg = data.get("ppg", {})
            ecg = data.get("ecg", {})
            temp = data.get("temp", {})
            dispenser = data.get("dispenser", {})
            return {
                "seq": int(data.get("seq", 0)),
                "ts": int(data.get("ts", 0)),
                "heart_rate": float(ppg.get("bpm", 0.0)) if ppg.get("bpm") is not None else None,
                "spo2": float(ppg.get("spo2", 0.0)) if ppg.get("spo2") is not None else None,
                "confidence": float(ppg.get("conf", 0.0)) if ppg.get("conf") is not None else None,
                "finger_detected": bool(ppg.get("finger", False)),
                "lead_off": bool(ecg.get("lead_off", False)),
                "raw_ecg": int(ecg.get("raw", 0)) if ecg.get("raw") is not None else None,
                "temperature_ambient": float(temp.get("amb", 0.0)) if temp.get("amb") is not None else None,
                "temperature_object": float(temp.get("obj", 0.0)) if temp.get("obj") is not None else None,
                "temperature_confidence": float(temp.get("conf", 0.0)) if temp.get("conf") is not None else None,
                "target_present": bool(temp.get("target", False)),
                "current_compartment": int(dispenser.get("comp", 0)) if dispenser.get("comp") is not None else None,
                "target_compartment": int(dispenser.get("target", 0)) if dispenser.get("target") is not None else None,
                "is_moving": bool(dispenser.get("moving", False)),
                "is_homed": bool(dispenser.get("homed", False)),
                "stall_detected": bool(dispenser.get("stall", False)),
                "battery_mv": int(data.get("bat", 0)) if data.get("bat") is not None else None,
                "status_flags": int(data.get("status", 0)) if data.get("status") is not None else None,
            }
        except Exception:
            return None

    def _handle_vitals_message(self, payload_bytes: bytes) -> None:
        parsed = self.parse_vitals_payload(payload_bytes)
        if not parsed:
            return
        self.received_packets_count += 1
        self.last_telemetry_time = datetime.now(timezone.utc)
        try:
            self.vitals_queue.put_nowait(parsed)
        except queue.Full:
            try:
                self.vitals_queue.get_nowait()
                self.vitals_queue.put_nowait(parsed)
            except Exception:
                pass

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            topic = getattr(msg, "topic", "")
            payload_bytes = getattr(msg, "payload", b"")
            if topic == settings.MQTT_TOPIC_STATUS:
                payload_str = payload_bytes.decode("utf-8", errors="ignore").strip()
                self._handle_status_message(payload_str)
            elif topic == settings.MQTT_TOPIC_VITALS_PROCESSED:
                self._handle_vitals_message(payload_bytes)
        except Exception as exc:
            logger.warning(f"Error handling MQTT message on {getattr(msg, 'topic', 'unknown')}: {exc}")

    def flush_vitals_batch(self, max_items: int = 50) -> int:
        batch: List[Dict[str, Any]] = []
        while len(batch) < max_items:
            try:
                item = self.vitals_queue.get_nowait()
                batch.append(item)
            except queue.Empty:
                break
        if not batch:
            return 0
        try:
            with Session(engine) as session:
                for item in batch:
                    uid = self.active_session_uid or "default"
                    vital = Vital(
                        session_uid=uid,
                        timestamp=datetime.now(timezone.utc),
                        heart_rate=item.get("heart_rate"),
                        spo2=item.get("spo2"),
                        confidence=item.get("confidence"),
                        raw_signal=str(item.get("raw_ecg")) if item.get("raw_ecg") is not None else None,
                        is_calibrated=False,
                        temperature_ambient=item.get("temperature_ambient"),
                        temperature_object=item.get("temperature_object"),
                        temperature_confidence=item.get("temperature_confidence"),
                        target_present=item.get("target_present"),
                        lead_off=item.get("lead_off"),
                        finger_detected=item.get("finger_detected"),
                        current_compartment=item.get("current_compartment"),
                        target_compartment=item.get("target_compartment"),
                        is_moving=item.get("is_moving"),
                        is_homed=item.get("is_homed"),
                        stall_detected=item.get("stall_detected"),
                        battery_mv=item.get("battery_mv"),
                        status_flags=item.get("status_flags"),
                    )
                    session.add(vital)
                session.commit()
            self.persisted_vitals_count += len(batch)
            return len(batch)
        except Exception as exc:
            logger.warning(f"Error persisting vitals batch: {exc}")
            return 0

    def _vitals_persistence_worker(self) -> None:
        while self.running:
            try:
                self.flush_vitals_batch(settings.MQTT_INGEST_BATCH_SIZE)
            except Exception as exc:
                logger.warning(f"Unexpected error in vitals worker: {exc}")
            time.sleep(settings.MQTT_INGEST_FLUSH_INTERVAL_SEC)
        try:
            self.flush_vitals_batch(100)
        except Exception:
            pass

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.state = MqttConnectionState.CONNECTING
        self._init_client()
        self._worker_thread = threading.Thread(target=self._vitals_persistence_worker, daemon=True)
        self._worker_thread.start()
        try:
            if self.client:
                self.client.connect_async(self.broker, self.port, keepalive=settings.MQTT_KEEPALIVE_SEC)
                self.client.loop_start()
        except Exception as exc:
            self.state = MqttConnectionState.RECONNECTING
            logger.warning(f"MQTT async connect initial attempt failed: {exc}")

    def stop(self) -> None:
        self.running = False
        if self._worker_thread and self._worker_thread.is_alive():
            try:
                self._worker_thread.join(timeout=2.0)
            except Exception:
                pass
        self._worker_thread = None
        if self.client:
            try:
                self.client.disconnect()
                self.client.loop_stop()
            except Exception:
                pass
        self.state = MqttConnectionState.DISCONNECTED
        self.droid_online = False


mqtt_ingest_service = MqttIngestService()
