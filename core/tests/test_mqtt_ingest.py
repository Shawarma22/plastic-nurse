import json
import struct
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.db.session import init_db, engine
from app.db.models import Vital, WaveformBatchRecord, Event
from app.services.mqtt_ingest_service import MqttIngestService
from app.services.waveform_parser import WaveformBatchParser


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


def test_waveform_batch_parser_roundtrip():
    samples = [
        {"ecg_raw": 512 + i, "ir_raw": 10000 + i * 10, "red_raw": 20000 + i * 20, "flags": i % 4}
        for i in range(16)
    ]
    packed = WaveformBatchParser.pack(
        batch_seq=42,
        start_ts_ms=1700000000,
        sample_interval_ms=20,
        samples=samples,
    )
    assert len(packed) == 16 + 16 * 11
    unpacked = WaveformBatchParser.unpack(packed)
    assert unpacked is not None
    assert unpacked["batch_seq"] == 42
    assert unpacked["sample_interval_ms"] == 20
    assert unpacked["sample_count"] == 16
    assert len(unpacked["samples"]) == 16
    for i, s in enumerate(unpacked["samples"]):
        assert s["ecg_raw"] == 512 + i
        assert s["ir_raw"] == 10000 + i * 10
        assert s["red_raw"] == 20000 + i * 20
        assert s["flags"] == i % 4


def test_waveform_batch_parser_invalid_magic_and_truncated():
    corrupted_magic = struct.pack("<BBHIIHH", 0x12, 0x34, 1, 1, 0, 20, 2) + b"\x00" * 22
    assert WaveformBatchParser.unpack(corrupted_magic) is None

    truncated = b"\xAA\x55\x01\x00"
    assert WaveformBatchParser.unpack(truncated) is None


def test_parse_vitals_payload():
    payload = {
        "seq": 101,
        "ts": 1700000050,
        "ppg": {
            "ir": 120000,
            "red": 145000,
            "bpm": 72.5,
            "spo2": 98.4,
            "conf": 0.94,
            "finger": True,
        },
        "ecg": {
            "raw": 2048,
            "lead_off": False,
        },
        "temp": {
            "amb": 24.1,
            "obj": 36.6,
            "conf": 0.98,
            "target": True,
        },
        "dispenser": {
            "comp": 3,
            "target": 3,
            "moving": False,
            "homed": True,
            "stall": False,
        },
        "bat": 3850,
        "status": 7,
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    parsed = MqttIngestService.parse_vitals_payload(payload_bytes)
    assert parsed is not None
    assert parsed["seq"] == 101
    assert parsed["ts"] == 1700000050
    assert parsed["heart_rate"] == 72.5
    assert parsed["spo2"] == 98.4
    assert parsed["confidence"] == 0.94
    assert parsed["finger_detected"] is True
    assert parsed["lead_off"] is False
    assert parsed["raw_ecg"] == 2048
    assert parsed["temperature_ambient"] == 24.1
    assert parsed["temperature_object"] == 36.6
    assert parsed["target_present"] is True
    assert parsed["current_compartment"] == 3
    assert parsed["target_compartment"] == 3
    assert parsed["is_moving"] is False
    assert parsed["is_homed"] is True
    assert parsed["stall_detected"] is False
    assert parsed["battery_mv"] == 3850
    assert parsed["status_flags"] == 7


def test_parse_vitals_payload_invalid():
    assert MqttIngestService.parse_vitals_payload(b"") is None
    assert MqttIngestService.parse_vitals_payload(b"not-json-content") is None
    assert MqttIngestService.parse_vitals_payload(b"12345") is None
    assert MqttIngestService.parse_vitals_payload(b"{}") is not None


def test_status_log_and_metrics():
    service = MqttIngestService(broker="127.0.0.1", port=1883, client_id="test_ingest")
    assert service.is_connected() is False
    assert service.is_droid_online() is False
    assert service.get_state() == "disconnected"

    metrics = service.get_metrics()
    assert metrics["droid_online"] is False
    assert metrics["client_id"] == "test_ingest"
    assert metrics["received_packets_count"] == 0

    service.set_active_session_uid("session-abc-123")
    assert service.active_session_uid == "session-abc-123"


def test_dispense_command_validation():
    service = MqttIngestService(broker="127.0.0.1", port=1883, client_id="test_ingest")
    assert service.publish_dispense_command("invalid_cmd", 0) is False
    assert service.publish_dispense_command("dispense", -1) is False
    assert service.publish_dispense_command("dispense", 14) is False
    assert service.publish_dispense_command("dispense", 2) is False


def test_batch_flush_vitals_persistence():
    service = MqttIngestService(broker="127.0.0.1", port=1883, client_id="test_ingest_vitals")
    service.set_active_session_uid("test-session-batch")

    v1 = {
        "heart_rate": 70.0,
        "spo2": 97.0,
        "confidence": 0.90,
        "is_calibrated": False,
        "finger_detected": True,
        "timestamp": datetime.now(timezone.utc),
    }
    v2 = {
        "heart_rate": 72.0,
        "spo2": 98.0,
        "confidence": 0.95,
        "is_calibrated": False,
        "finger_detected": True,
        "timestamp": datetime.now(timezone.utc),
    }
    service.vitals_queue.put(v1)
    service.vitals_queue.put(v2)

    persisted = service.flush_vitals_batch(10)
    assert persisted == 2
    assert service.persisted_vitals_count == 2
    assert service.vitals_queue.empty() is True

    with Session(engine) as session:
        records = session.exec(select(Vital).where(Vital.session_uid == "test-session-batch")).all()
        assert len(records) == 2


def test_batch_flush_waveform_persistence():
    service = MqttIngestService(broker="127.0.0.1", port=1883, client_id="test_ingest_wave")
    service.set_active_session_uid("test-session-wave")

    samples = [{"ecg_raw": 100, "ir_raw": 5000, "red_raw": 8000, "flags": 0}]
    raw = WaveformBatchParser.pack(
        batch_seq=1,
        start_ts_ms=1700000000,
        sample_interval_ms=20,
        samples=samples,
    )
    service.waveform_queue.put({
        "batch_seq": 1,
        "sample_interval_ms": 20,
        "sample_count": 1,
        "raw_bytes": raw,
        "timestamp": datetime.now(timezone.utc),
    })

    persisted = service.flush_waveform_batch(10)
    assert persisted == 1
    assert service.persisted_batches_count == 1
    assert service.waveform_queue.empty() is True

    with Session(engine) as session:
        records = session.exec(select(WaveformBatchRecord).where(WaveformBatchRecord.session_uid == "test-session-wave")).all()
        assert len(records) == 1
        assert records[0].batch_seq == 1


def test_batch_flush_events_persistence():
    service = MqttIngestService(broker="127.0.0.1", port=1883, client_id="test_ingest_evt")
    service.set_active_session_uid("test-session-evt")

    service.events_queue.put({
        "event_type": "carousel_stall",
        "payload": json.dumps({"compartment": 4}),
        "timestamp": datetime.now(timezone.utc),
    })

    persisted = service.flush_events_batch(10)
    assert persisted == 1
    assert service.persisted_events_count == 1
    assert service.events_queue.empty() is True

    with Session(engine) as session:
        records = session.exec(select(Event).where(Event.session_uid == "test-session-evt")).all()
        assert len(records) == 1
        assert records[0].event_type == "carousel_stall"


def test_telemetry_rest_status_and_session(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    res = client.get("/api/v1/telemetry/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "droid_online" in data
    assert "broker" in data

    set_res = client.post(
        "/api/v1/telemetry/session",
        json={"session_uid": "integration-test-uid"},
        headers=headers,
    )
    assert set_res.status_code == 200
    assert set_res.json()["active_session_uid"] == "integration-test-uid"

    path_res = client.post(
        "/api/v1/telemetry/session/path-test-uid",
        headers=headers,
    )
    assert path_res.status_code == 200
    assert path_res.json()["active_session_uid"] == "path-test-uid"


def test_telemetry_rest_dispense_failure_when_offline(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    res = client.post(
        "/api/v1/telemetry/dispense",
        json={"cmd": "dispense", "compartment": 2},
        headers=headers,
    )
    assert res.status_code == 400
