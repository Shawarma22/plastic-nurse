from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)

class FaceDetectionResult(BaseModel):
    detected: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    landmark_count: int = 0

class BaseFaceDetector(ABC):
    @abstractmethod
    def detect_faces(self, frame_bytes: bytes) -> List[FaceDetectionResult]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
