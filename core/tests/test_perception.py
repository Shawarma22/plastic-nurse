from fastapi.testclient import TestClient
from app.perception.base import BoundingBox, FaceDetectionResult
from app.perception.mock import MockFaceDetector
from app.perception.cues import BehavioralCue, evaluate_frame_cue
from app.perception.smoother import TemporalSmoother
from app.perception.service import PerceptionService

def test_mock_face_detector():
    detector = MockFaceDetector(face_present=True, confidence=0.88)
    results = detector.detect_faces(b"fake_frame_data")
    assert len(results) == 1
    res = results[0]
    assert res.detected is True
    assert res.confidence == 0.88
    assert res.bounding_box is not None
    assert 0.0 <= res.bounding_box.x_min <= 1.0
    assert 0.0 <= res.bounding_box.y_min <= 1.0
    assert 0.0 <= res.bounding_box.width <= 1.0
    assert 0.0 <= res.bounding_box.height <= 1.0

    detector.set_face_present(False)
    results_empty = detector.detect_faces(b"fake_frame_data")
    assert len(results_empty) == 1
    assert results_empty[0].detected is False

    detector.close()
    assert detector.is_closed is True

def test_temporal_smoother_majority_vote():
    smoother = TemporalSmoother(window_size=5)
    assert smoother.is_full() is False

    winner, stability = smoother.add_sample(BehavioralCue.ENGAGED)
    assert winner == BehavioralCue.ENGAGED
    assert stability == 1.0

    smoother.add_sample(BehavioralCue.ENGAGED)
    smoother.add_sample(BehavioralCue.NEUTRAL)
    smoother.add_sample(BehavioralCue.ENGAGED)
    winner, stability = smoother.add_sample(BehavioralCue.DISTRESS_FLAGGED)

    assert smoother.is_full() is True
    assert winner == BehavioralCue.ENGAGED
    assert stability == 0.60
    assert len(smoother.get_history()) == 5

    smoother.clear()
    assert len(smoother.get_history()) == 0

def test_evaluate_frame_cue():
    assert evaluate_frame_cue([]) == BehavioralCue.ABSENT
    assert evaluate_frame_cue([FaceDetectionResult(detected=False, confidence=0.0)]) == BehavioralCue.ABSENT

    engaged_det = [
        FaceDetectionResult(
            detected=True,
            confidence=0.92,
            bounding_box=BoundingBox(x_min=0.2, y_min=0.2, width=0.4, height=0.4)
        )
    ]
    assert evaluate_frame_cue(engaged_det) == BehavioralCue.ENGAGED

    distress_det = [
        FaceDetectionResult(
            detected=True,
            confidence=0.35,
            bounding_box=BoundingBox(x_min=0.2, y_min=0.2, width=0.4, height=0.4)
        )
    ]
    assert evaluate_frame_cue(distress_det) == BehavioralCue.DISTRESS_FLAGGED

    neutral_det = [
        FaceDetectionResult(
            detected=True,
            confidence=0.70,
            bounding_box=BoundingBox(x_min=0.2, y_min=0.2, width=0.4, height=0.4)
        )
    ]
    assert evaluate_frame_cue(neutral_det) == BehavioralCue.NEUTRAL

def test_perception_service_pipeline():
    mock_det = MockFaceDetector(face_present=True, confidence=0.9)
    service = PerceptionService(detector=mock_det, window_size=3)

    state = service.process_frame(b"frame1")
    assert state.face_detected is True
    assert state.cue == BehavioralCue.ENGAGED

    mock_det.set_face_present(False)
    service.process_frame(b"frame2")
    state3 = service.process_frame(b"frame3")
    assert state3.cue == BehavioralCue.ABSENT

    service.close()

def test_perception_api_endpoints(client: TestClient, operator_token: str):
    res_unauth = client.get("/api/v1/perception/status")
    assert res_unauth.status_code == 401

    headers = {"Authorization": f"Bearer {operator_token}"}
    res_status = client.get("/api/v1/perception/status", headers=headers)
    assert res_status.status_code == 200
    data = res_status.json()
    assert "cue" in data
    assert "confidence" in data
    assert "face_detected" in data

    res_analyze = client.post("/api/v1/perception/analyze", headers=headers)
    assert res_analyze.status_code == 200
    analyze_data = res_analyze.json()
    assert "cue" in analyze_data
    assert "confidence" in analyze_data
