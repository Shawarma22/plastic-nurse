from typing import Optional
from app.config import settings
from app.perception.base import BaseFaceDetector
from app.perception.mock import MockFaceDetector
from app.perception.detector import MediaPipeFaceDetector
from app.perception.cues import BehavioralCue, PerceptionState, evaluate_frame_cue
from app.perception.smoother import TemporalSmoother

class PerceptionService:
    def __init__(
        self,
        detector: Optional[BaseFaceDetector] = None,
        window_size: int = 5
    ) -> None:
        if detector is not None:
            self.detector = detector
        elif settings.DROID_HAL == "real":
            self.detector = MediaPipeFaceDetector()
        else:
            self.detector = MockFaceDetector()
        self.smoother = TemporalSmoother(window_size=window_size)
        self.latest_state = PerceptionState(
            cue=BehavioralCue.ABSENT,
            confidence=0.0,
            face_detected=False,
            detections_count=0,
            window_size=window_size
        )

    def process_frame(self, frame_bytes: bytes) -> PerceptionState:
        detections = self.detector.detect_faces(frame_bytes)
        face_detected = any(d.detected for d in detections)
        raw_cue = evaluate_frame_cue(detections)
        smoothed_cue, stability = self.smoother.add_sample(raw_cue)
        self.latest_state = PerceptionState(
            cue=smoothed_cue,
            confidence=stability,
            face_detected=face_detected,
            detections_count=len(detections) if face_detected else 0,
            window_size=self.smoother.window_size
        )
        return self.latest_state

    def get_status(self) -> PerceptionState:
        return self.latest_state

    def close(self) -> None:
        self.detector.close()

perception_service = PerceptionService()
