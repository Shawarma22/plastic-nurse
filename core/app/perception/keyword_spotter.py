from typing import Optional
from app.perception.wake_base import BaseWakeWordDetector, WakeWordDetectionResult
from app.perception.wake_mock import MockWakeWordDetector
from app.perception.energy_vad import EnergyVAD
from app.perception.audio_buffer import AudioRingBuffer

class KeywordSpotter(BaseWakeWordDetector):
    def __init__(
        self,
        wake_word: str = "hey droid",
        vad_threshold: float = 400.0,
        buffer_seconds: float = 2.0,
        sample_rate: int = 16000
    ) -> None:
        self.wake_word = wake_word.lower()
        self.sample_rate = sample_rate
        bytes_per_sec = sample_rate * 2
        buffer_capacity = int(buffer_seconds * bytes_per_sec)
        self.vad = EnergyVAD(threshold=vad_threshold, sample_rate=sample_rate)
        self.ring_buffer = AudioRingBuffer(capacity_bytes=buffer_capacity)
        self._fallback: Optional[MockWakeWordDetector] = MockWakeWordDetector(wake_word=self.wake_word)
        self._active = True

    def process_audio_chunk(self, chunk: bytes) -> WakeWordDetectionResult:
        if not self._active or not chunk:
            return WakeWordDetectionResult(detected=False)

        self.ring_buffer.write(chunk)
        if not self.vad.is_speech(chunk):
            return WakeWordDetectionResult(detected=False)

        if self._fallback is not None:
            return self._fallback.process_audio_chunk(chunk)

        return WakeWordDetectionResult(detected=False)

    def trigger_test_wake(self, confidence: float = 0.95) -> None:
        if self._fallback:
            self._fallback.trigger_next(confidence)

    def reset(self) -> None:
        self.ring_buffer.clear()
        if self._fallback:
            self._fallback.reset()

    def is_active(self) -> bool:
        return self._active
