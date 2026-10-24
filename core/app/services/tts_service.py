import hashlib
import os
import re
from enum import Enum
from pathlib import Path
import threading
from typing import List, Optional
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
        self.cache_dir = Path(self.config.TTS_CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_state(self) -> AudioOutputState:
        with self._lock:
            return self.state

    def set_state(self, new_state: AudioOutputState) -> None:
        with self._lock:
            self.state = new_state

    def get_cache_path(self, text: str, engine: Optional[str] = None) -> Path:
        engine_name = engine or self.engine_type
        key = f"{engine_name}:{self.config.PIPER_SPEAKER_ID}:{text.strip()}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.wav"

    def is_cached(self, text: str, engine: Optional[str] = None) -> bool:
        return self.get_cache_path(text, engine).is_file()

    def get_cached_audio(self, text: str, engine: Optional[str] = None) -> Optional[bytes]:
        path = self.get_cache_path(text, engine)
        if path.is_file():
            return path.read_bytes()
        return None

    def cache_audio(self, text: str, audio_bytes: bytes, engine: Optional[str] = None) -> Path:
        path = self.get_cache_path(text, engine)
        path.write_bytes(audio_bytes)
        return path

    def clear_cache(self) -> int:
        count = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.wav"):
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    pass
        return count

    def clean_text(self, text: str) -> str:
        cleaned = re.sub(r"[\r\n\t]+", " ", text)
        cleaned = re.sub(r"[^\w\s.,!?;:\'\"-]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def chunk_text(self, text: str, max_chunk_words: int = 25) -> List[str]:
        cleaned = self.clean_text(text)
        if not cleaned:
            return []
        raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        chunks: List[str] = []
        for sentence in raw_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            words = sentence.split()
            if len(words) <= max_chunk_words:
                chunks.append(sentence)
            else:
                clause_parts = re.split(r"(?<=[,;:])\s+", sentence)
                current_clause: List[str] = []
                current_word_count = 0
                for part in clause_parts:
                    part = part.strip()
                    if not part:
                        continue
                    part_words = len(part.split())
                    if current_word_count + part_words <= max_chunk_words:
                        current_clause.append(part)
                        current_word_count += part_words
                    else:
                        if current_clause:
                            chunks.append(" ".join(current_clause))
                        current_clause = [part]
                        current_word_count = part_words
                if current_clause:
                    chunks.append(" ".join(current_clause))
        return chunks if chunks else [cleaned]
