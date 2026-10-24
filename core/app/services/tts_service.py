from enum import Enum
import threading
from typing import Optional
from app.config import settings, Settings


class AudioOutputState(str, Enum):
    IDLE = "idle"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    ERROR = "error"


class TtsService:
    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self.state = AudioOutputState.IDLE
        self._lock = threading.Lock()
        self.current_utterance_id: Optional[str] = None
        self.engine_type = self.config.TTS_ENGINE

    def get_state(self) -> AudioOutputState:
        with self._lock:
            return self.state

    def set_state(self, new_state: AudioOutputState) -> None:
        with self._lock:
            self.state = new_state
