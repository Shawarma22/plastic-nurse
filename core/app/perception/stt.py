from abc import ABC, abstractmethod
import json
import os
from typing import Optional, List
from pydantic import BaseModel
from app.config import settings
from app.logger import logger

class SpeechTranscriptResult(BaseModel):
    transcript: str
    is_final: bool
    confidence: float = 1.0

class BaseSpeechRecognizer(ABC):
    @abstractmethod
    def accept_waveform(self, chunk_bytes: bytes) -> Optional[SpeechTranscriptResult]:
        pass

    @abstractmethod
    def get_final_result(self) -> SpeechTranscriptResult:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

class MockSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(self, predefined_transcripts: Optional[List[str]] = None) -> None:
        self.transcripts = predefined_transcripts or ["check vitals", "open door"]
        self._current_index = 0
        self._buffer_size = 0
        self._threshold = 8192

    def enqueue_transcript(self, text: str) -> None:
        self.transcripts.append(text)

    def accept_waveform(self, chunk_bytes: bytes) -> Optional[SpeechTranscriptResult]:
        if not chunk_bytes:
            return None
        self._buffer_size += len(chunk_bytes)
        if self._buffer_size >= self._threshold:
            self._buffer_size = 0
            if self.transcripts:
                text = self.transcripts[self._current_index % len(self.transcripts)]
                self._current_index += 1
                return SpeechTranscriptResult(transcript=text, is_final=True, confidence=0.95)
        return SpeechTranscriptResult(transcript="", is_final=False, confidence=0.50)

    def get_final_result(self) -> SpeechTranscriptResult:
        text = self.transcripts[(self._current_index - 1) % len(self.transcripts)] if self.transcripts else ""
        return SpeechTranscriptResult(transcript=text, is_final=True, confidence=0.95)

    def reset(self) -> None:
        self._buffer_size = 0

class VoskSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: Optional[int] = None
    ) -> None:
        self.model_path = model_path or settings.VOSK_MODEL_PATH
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self._recognizer = None
        self._model = None
        self._fallback: Optional[MockSpeechRecognizer] = None
        self._init_vosk()

    def _init_vosk(self) -> None:
        if os.path.exists(self.model_path):
            try:
                import vosk
                vosk.SetLogLevel(-1)
                self._model = vosk.Model(self.model_path)
                self._recognizer = vosk.KaldiRecognizer(self._model, float(self.sample_rate))
                logger.info(f"Loaded Vosk model from {self.model_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load Vosk: {e}. Using mock fallback.")
        self._fallback = MockSpeechRecognizer()

    def accept_waveform(self, chunk_bytes: bytes) -> Optional[SpeechTranscriptResult]:
        if self._fallback is not None:
            return self._fallback.accept_waveform(chunk_bytes)
        if not chunk_bytes or self._recognizer is None:
            return None
        try:
            if self._recognizer.AcceptWaveform(chunk_bytes):
                res = json.loads(self._recognizer.Result())
                text = res.get("text", "")
                return SpeechTranscriptResult(transcript=text, is_final=True, confidence=0.95)
            partial = json.loads(self._recognizer.PartialResult())
            text = partial.get("partial", "")
            return SpeechTranscriptResult(transcript=text, is_final=False, confidence=0.70)
        except Exception as e:
            logger.error(f"Vosk recognition error: {e}")
            return None

    def get_final_result(self) -> SpeechTranscriptResult:
        if self._fallback is not None:
            return self._fallback.get_final_result()
        if self._recognizer is None:
            return SpeechTranscriptResult(transcript="", is_final=True, confidence=0.0)
        try:
            res = json.loads(self._recognizer.FinalResult())
            text = res.get("text", "")
            return SpeechTranscriptResult(transcript=text, is_final=True, confidence=0.95)
        except Exception as e:
            logger.error(f"Vosk final result error: {e}")
            return SpeechTranscriptResult(transcript="", is_final=True, confidence=0.0)

    def reset(self) -> None:
        if self._fallback is not None:
            self._fallback.reset()
        elif self._recognizer is not None and self._model is not None:
            import vosk
            self._recognizer = vosk.KaldiRecognizer(self._model, float(self.sample_rate))
