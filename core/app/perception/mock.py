from typing import List
from app.perception.base import BaseFaceDetector, FaceDetectionResult, BoundingBox

class MockFaceDetector(BaseFaceDetector):
    def __init__(self, face_present: bool = True, confidence: float = 0.9) -> None:
        self.face_present = face_present
        self.confidence = max(0.0, min(1.0, confidence))
        self.is_closed = False

    def set_face_present(self, present: bool, confidence: float = 0.9) -> None:
        self.face_present = present
        self.confidence = max(0.0, min(1.0, confidence))

    def detect_faces(self, frame_bytes: bytes) -> List[FaceDetectionResult]:
        if self.is_closed or not self.face_present or not frame_bytes:
            return [FaceDetectionResult(detected=False, confidence=0.0)]
        bbox = BoundingBox(
            x_min=0.25,
            y_min=0.20,
            width=0.50,
            height=0.60
        )
        return [
            FaceDetectionResult(
                detected=True,
                confidence=self.confidence,
                bounding_box=bbox,
                landmark_count=6
            )
        ]

    def close(self) -> None:
        self.is_closed = True
