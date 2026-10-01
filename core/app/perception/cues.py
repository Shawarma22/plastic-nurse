from enum import Enum
from typing import List, Dict, Any
import time
from pydantic import BaseModel, Field
from app.perception.base import FaceDetectionResult

class BehavioralCue(str, Enum):
    ENGAGED = "engaged"
    DISTRESS_FLAGGED = "distress_flagged"
    NEUTRAL = "neutral"
    ABSENT = "absent"

class PerceptionState(BaseModel):
    cue: BehavioralCue
    confidence: float = Field(ge=0.0, le=1.0)
    face_detected: bool
    detections_count: int
    window_size: int
    timestamp: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cue": self.cue.value,
            "confidence": self.confidence,
            "face_detected": self.face_detected,
            "detections_count": self.detections_count,
            "window_size": self.window_size,
            "timestamp": self.timestamp
        }

def evaluate_frame_cue(detections: List[FaceDetectionResult]) -> BehavioralCue:
    if not detections or not any(d.detected for d in detections):
        return BehavioralCue.ABSENT
    valid = [d for d in detections if d.detected]
    primary = max(valid, key=lambda d: d.confidence)
    if primary.confidence >= 0.85:
        return BehavioralCue.ENGAGED
    if primary.confidence < 0.4:
        return BehavioralCue.DISTRESS_FLAGGED
    return BehavioralCue.NEUTRAL
