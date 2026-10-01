from typing import List
import numpy as np
import cv2
from app.perception.base import BaseFaceDetector, FaceDetectionResult, BoundingBox
from app.perception.mock import MockFaceDetector
from app.logger import logger

class MediaPipeFaceDetector(BaseFaceDetector):
    def __init__(self, min_detection_confidence: float = 0.5) -> None:
        self.min_confidence = min_detection_confidence
        self._mp_detector = None
        self._fallback = None
        self._init_detector()

    def _init_detector(self) -> None:
        try:
            import mediapipe as mp
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_detection"):
                self._mp_detector = mp.solutions.face_detection.FaceDetection(
                    min_detection_confidence=self.min_confidence,
                    model_selection=0
                )
                logger.info("Initialized MediaPipe FaceDetection pipeline")
            else:
                logger.warning("MediaPipe solutions unavailable, using mock face detector fallback")
                self._fallback = MockFaceDetector(face_present=True, confidence=0.85)
        except Exception as e:
            logger.warning(f"Failed to load MediaPipe: {e}. Falling back to mock face detector")
            self._fallback = MockFaceDetector(face_present=True, confidence=0.85)

    def detect_faces(self, frame_bytes: bytes) -> List[FaceDetectionResult]:
        if self._fallback is not None:
            return self._fallback.detect_faces(frame_bytes)
        if not frame_bytes or self._mp_detector is None:
            return [FaceDetectionResult(detected=False, confidence=0.0)]
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return [FaceDetectionResult(detected=False, confidence=0.0)]
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self._mp_detector.process(rgb_img)
            if not results.detections:
                return [FaceDetectionResult(detected=False, confidence=0.0)]
            out: List[FaceDetectionResult] = []
            for det in results.detections:
                score = float(det.score[0]) if det.score else 0.0
                bbox_data = det.location_data.relative_bounding_box
                x_min = max(0.0, min(1.0, float(bbox_data.xmin)))
                y_min = max(0.0, min(1.0, float(bbox_data.ymin)))
                w = max(0.0, min(1.0 - x_min, float(bbox_data.width)))
                h = max(0.0, min(1.0 - y_min, float(bbox_data.height)))
                bbox = BoundingBox(x_min=x_min, y_min=y_min, width=w, height=h)
                landmarks = len(det.location_data.relative_keypoints) if hasattr(det.location_data, "relative_keypoints") else 0
                out.append(
                    FaceDetectionResult(
                        detected=True,
                        confidence=round(score, 2),
                        bounding_box=bbox,
                        landmark_count=landmarks
                    )
                )
            return out
        except Exception as e:
            logger.error(f"MediaPipe detection failure: {e}")
            return [FaceDetectionResult(detected=False, confidence=0.0)]

    def close(self) -> None:
        if self._mp_detector is not None:
            try:
                self._mp_detector.close()
            except Exception:
                pass
            self._mp_detector = None
        if self._fallback is not None:
            self._fallback.close()
