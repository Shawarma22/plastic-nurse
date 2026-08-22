from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["hal_mode"] == "mock"

def test_vitals_session_and_records(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    sess_res = client.post(
        "/api/v1/vitals/sessions",
        json={"patient_ref": "PATIENT-101", "notes": "Initial test routine"},
        headers=headers
    )
    assert sess_res.status_code == 201
    sess_data = sess_res.json()
    session_uid = sess_data["session_uid"]
    assert sess_data["patient_ref"] == "PATIENT-101"

    vit_res = client.post(
        "/api/v1/vitals/records",
        json={
            "session_uid": session_uid,
            "heart_rate": 74.5,
            "spo2": 98.2,
            "confidence": 0.92,
            "is_calibrated": False
        },
        headers=headers
    )
    assert vit_res.status_code == 201
    vit_data = vit_res.json()
    assert vit_data["heart_rate"] == 74.5
    assert vit_data["spo2"] == 98.2
    assert vit_data["is_calibrated"] is False

    get_vit_res = client.get(f"/api/v1/vitals/records/{session_uid}", headers=headers)
    assert get_vit_res.status_code == 200
    assert len(get_vit_res.json()) == 1

def test_events_recording(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    evt_res = client.post(
        "/api/v1/vitals/events",
        json={
            "session_uid": "test-session-xyz",
            "event_type": "face_distress_cue_flagged",
            "payload": "{\"confidence\": 0.85}"
        },
        headers=headers
    )
    assert evt_res.status_code == 201
    evt_data = evt_res.json()
    assert evt_data["event_type"] == "face_distress_cue_flagged"

def test_jobs_submission_and_query(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    submit_res = client.post(
        "/api/v1/jobs/submit",
        json={"job_type": "sensor_calibration", "payload": {"target": "mock"}},
        headers=headers
    )
    assert submit_res.status_code == 202
    job_id = submit_res.json()["job_id"]

    query_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert query_res.status_code == 200
    assert query_res.json()["job_id"] == job_id

def test_camera_snapshot(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}
    response = client.get("/api/v1/camera/snapshot", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert len(response.content) > 0
