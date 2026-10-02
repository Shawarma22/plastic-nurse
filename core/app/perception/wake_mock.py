from app.perception.wake_base import BaseWakeWordDetector, WakeWordDetectionResult

class MockWakeWordDetector(BaseWakeWordDetector):
    def __init__(
        self,
        wake_word: str = "hey droid",
        auto_trigger_after_chunks: int = 5,
        confidence: float = 0.95
    ) -> None:
        self.wake_word = wake_word
        self.auto_trigger_threshold = auto_trigger_after_chunks
        self.confidence = max(0.0, min(1.0, confidence))
        self._chunk_counter = 0
        self._manual_trigger = False
        self._is_active = True

    def trigger_next(self, confidence: float = 0.95) -> None:
        self._manual_trigger = True
        self.confidence = max(0.0, min(1.0, confidence))

    def process_audio_chunk(self, chunk: bytes) -> WakeWordDetectionResult:
        if not self._is_active or not chunk:
            return WakeWordDetectionResult(detected=False)

        if self._manual_trigger:
            self._manual_trigger = False
            return WakeWordDetectionResult(
                detected=True,
                wake_word=self.wake_word,
                confidence=self.confidence
            )

        self._chunk_counter += 1
        if self.auto_trigger_threshold > 0 and self._chunk_counter >= self.auto_trigger_threshold:
            self._chunk_counter = 0
            return WakeWordDetectionResult(
                detected=True,
                wake_word=self.wake_word,
                confidence=self.confidence
            )

        return WakeWordDetectionResult(detected=False)

    def reset(self) -> None:
        self._chunk_counter = 0
        self._manual_trigger = False

    def is_active(self) -> bool:
        return self._is_active
