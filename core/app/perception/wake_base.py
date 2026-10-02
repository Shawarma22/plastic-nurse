from abc import ABC, abstractmethod
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class WakeWordDetectionResult(BaseModel):
    detected: bool
    wake_word: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "wake_word": self.wake_word,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }

class BaseWakeWordDetector(ABC):
    @abstractmethod
    def process_audio_chunk(self, chunk: bytes) -> WakeWordDetectionResult:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass
