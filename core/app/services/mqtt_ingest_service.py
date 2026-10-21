import queue
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt
from app.config import settings
from app.logger import logger


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
        self.client: Optional[mqtt.Client] = None
        self.running = False
        self.vitals_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.waveform_queue: queue.Queue = queue.Queue(maxsize=500)
        self.events_queue: queue.Queue = queue.Queue(maxsize=500)

    def is_connected(self) -> bool:
        return self.state == MqttConnectionState.CONNECTED

    def is_droid_online(self) -> bool:
        return self.droid_online

    def get_state(self) -> str:
        return self.state.value

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "droid_online": self.droid_online,
            "broker": f"{self.broker}:{self.port}",
            "client_id": self.client_id,
            "last_status_time": self.last_status_time.isoformat() if self.last_status_time else None,
            "last_telemetry_time": self.last_telemetry_time.isoformat() if self.last_telemetry_time else None,
            "received_packets_count": self.received_packets_count,
            "received_batches_count": self.received_batches_count,
            "received_events_count": self.received_events_count,
            "vitals_queue_size": self.vitals_queue.qsize(),
            "waveform_queue_size": self.waveform_queue.qsize(),
            "events_queue_size": self.events_queue.qsize(),
        }

    def start(self) -> None:
        self.running = True
        self.state = MqttConnectionState.CONNECTING

    def stop(self) -> None:
        self.running = False
        self.state = MqttConnectionState.DISCONNECTED


mqtt_ingest_service = MqttIngestService()
