import json
import struct
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.db.session import init_db, engine
from app.db.models import Session as DBSession, Vital, BloodPressureRecord, Event
from app.services.ble_bp_parser import BleBloodPressureParser, parse_sfloat, pack_sfloat
from app.services.ble_bp_service import ble_bp_service
from app.services.alert_engine import alert_engine
from app.services.export_service import export_service


@pytest.fixture(autouse=True)
def ensure_db():
    init_db()


def test_sfloat_packing_and_unpacking():
    val = 120.0
    packed = pack_sfloat(val, 0)
    unpacked = parse_sfloat(packed)
    assert unpacked == 120.0

    packed_neg = pack_sfloat(-15.0, 0)
    unpacked_neg = parse_sfloat(packed_neg)
    assert unpacked_neg == -15.0

    assert parse_sfloat(0x07FE) == float("inf")
    assert parse_sfloat(0x0802) == float("-inf")
    assert parse_sfloat(0x07FF) is None


def test_ble_bp_parser_roundtrip():
    now = datetime(2026, 10, 22, 4, 0, 0, tzinfo=timezone.utc)
    packed = BleBloodPressureParser.pack(
        systolic=124.0,
        diastolic=82.0,
        mean_arterial_pressure=96.0,
        pulse_rate=68.0,
        unit="mmHg",
        dt=now,
        user_id=1,
        status_flags=0x0002,
    )
    unpacked = BleBloodPressureParser.unpack(packed)
    assert unpacked is not None
    assert unpacked["systolic"] == 124.0
    assert unpacked["diastolic"] == 82.0
    assert unpacked["mean_arterial_pressure"] == 96.0
    assert unpacked["pulse_rate"] == 68.0
    assert unpacked["unit"] == "mmHg"
    assert unpacked["timestamp"] == now
    assert unpacked["user_id"] == 1
    assert unpacked["status_flags"] == 0x0002


def test_ble_bp_parser_corrupted():
    assert BleBloodPressureParser.unpack(b"") is None
    assert BleBloodPressureParser.unpack(b"\x00\x01\x02") is None


def test_ble_bp_service_persistence():
    sess_uid = "test-session-bp-persist"
    ble_bp_service.set_active_session_uid(sess_uid)

    rec = ble_bp_service.trigger_mock_measurement(
        systolic=118.0,
        diastolic=78.0,
        pulse_rate=66.0,
    )
    assert rec is not None
    assert rec["systolic"] == 118.0
    assert rec["diastolic"] == 78.0

    flushed = ble_bp_service.flush_measurements_batch(10)
    assert flushed >= 1

    with Session(engine) as session:
        records = session.exec(
            select(BloodPressureRecord).where(BloodPressureRecord.session_uid == sess_uid)
        ).all()
        assert len(records) >= 1
        assert records[0].systolic == 118.0
        assert records[0].diastolic == 78.0


def test_alert_engine_vitals_evaluation():
    alert_engine._last_alert_timestamps.clear()
    vital_high = {
        "session_uid": "test-alert-session",
        "heart_rate": 145.0,
        "spo2": 98.0,
        "confidence": 0.95,
        "finger_detected": True,
        "temperature_object": 36.5,
    }
    alerts = alert_engine.evaluate_vitals(vital_high)
    assert len(alerts) >= 1
    assert alerts[0]["parameter"] == "heart_rate_high"
    assert alerts[0]["severity"] == "warning"

    alerts_cooldown = alert_engine.evaluate_vitals(vital_high)
    assert len(alerts_cooldown) == 0


def test_alert_engine_spo2_and_temp():
    alert_engine._last_alert_timestamps.clear()
    vital_spo2 = {
        "session_uid": "test-alert-spo2",
        "heart_rate": 75.0,
        "spo2": 88.0,
        "confidence": 0.92,
        "finger_detected": True,
        "temperature_object": 39.0,
        "target_present": True,
    }
    alerts = alert_engine.evaluate_vitals(vital_spo2)
    params = [a["parameter"] for a in alerts]
    assert "spo2_low" in params
    assert "temp_obj_high" in params


def test_alert_engine_bp_evaluation():
    alert_engine._last_alert_timestamps.clear()
    bp_high = {
        "session_uid": "test-alert-bp",
        "systolic": 170.0,
        "diastolic": 105.0,
        "unit": "mmHg",
    }
    alerts = alert_engine.evaluate_blood_pressure(bp_high)
    params = [a["parameter"] for a in alerts]
    assert "bp_systolic_high" in params
    assert "bp_diastolic_high" in params


def test_export_service_flow():
    sess_uid = "test-export-session-101"
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        db_sess = DBSession(
            session_uid=sess_uid,
            patient_ref="PATIENT-EXP-01",
            status="completed",
            notes="Full observation session",
            start_time=now,
            end_time=now,
        )
        vit = Vital(
            session_uid=sess_uid,
            timestamp=now,
            heart_rate=72.0,
            spo2=98.0,
            temperature_object=36.7,
            confidence=0.95,
        )
        bp = BloodPressureRecord(
            session_uid=sess_uid,
            timestamp=now,
            systolic=120.0,
            diastolic=80.0,
            mean_arterial_pressure=93.0,
            pulse_rate=72.0,
        )
        ev = Event(
            session_uid=sess_uid,
            timestamp=now,
            event_type="test_marker",
            payload="marker-payload",
        )
        session.add(db_sess)
        session.add(vit)
        session.add(bp)
        session.add(ev)
        session.commit()

        json_data = export_service.export_json(sess_uid, session)
        assert json_data is not None
        assert json_data["patient_ref"] == "PATIENT-EXP-01"
        assert json_data["statistics"]["vitals_count"] == 1
        assert json_data["statistics"]["blood_pressure_count"] == 1
        assert "DISCLAIMER" in json_data["disclaimer"]

        csv_data = export_service.export_csv(sess_uid, session)
        assert csv_data is not None
        assert "PATIENT-EXP-01" in csv_data
        assert "DISCLAIMER" in csv_data
        assert "vital" in csv_data
        assert "blood_pressure" in csv_data

        report_data = export_service.export_summary_report(sess_uid, session)
        assert report_data is not None
        assert "MEDICAL ASSISTIVE DROID - SESSION TELEMETRY REPORT" in report_data
        assert "PATIENT-EXP-01" in report_data
        assert "REGULATORY NOTICE" in report_data


def test_telemetry_rest_day7_endpoints(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}

    bp_status_res = client.get("/api/v1/telemetry/bp/status", headers=headers)
    assert bp_status_res.status_code == 200
    assert "is_connected" in bp_status_res.json()

    measure_res = client.post(
        "/api/v1/telemetry/bp/mock-measure",
        json={"systolic": 125.0, "diastolic": 82.0, "pulse_rate": 70.0},
        headers=headers,
    )
    assert measure_res.status_code == 200
    assert measure_res.json()["systolic"] == 125.0

    alerts_res = client.get("/api/v1/telemetry/alerts/recent", headers=headers)
    assert alerts_res.status_code == 200
    assert isinstance(alerts_res.json(), list)

    create_sess_res = client.post(
        "/api/v1/vitals/sessions",
        json={"patient_ref": "PAT-XYZ", "notes": "Export test session"},
        headers=headers,
    )
    assert create_sess_res.status_code == 201
    sess_uid = create_sess_res.json()["session_uid"]

    vit_res = client.post(
        "/api/v1/vitals/records",
        json={
            "session_uid": sess_uid,
            "heart_rate": 80.0,
            "spo2": 99.0,
            "confidence": 0.95,
            "is_calibrated": False,
        },
        headers=headers,
    )
    assert vit_res.status_code == 201

    export_json_res = client.get(f"/api/v1/telemetry/export/json/{sess_uid}", headers=headers)
    assert export_json_res.status_code == 200
    assert export_json_res.json()["patient_ref"] == "PAT-XYZ"

    export_csv_res = client.get(f"/api/v1/telemetry/export/csv/{sess_uid}", headers=headers)
    assert export_csv_res.status_code == 200
    assert "text/csv" in export_csv_res.headers.get("content-type", "")

    export_rep_res = client.get(f"/api/v1/telemetry/export/report/{sess_uid}", headers=headers)
    assert export_rep_res.status_code == 200
    assert "text/plain" in export_rep_res.headers.get("content-type", "")
