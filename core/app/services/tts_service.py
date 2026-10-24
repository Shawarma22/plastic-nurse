import hashlib
import os
import re
import shutil
import struct
import subprocess
import time
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

    def generate_mock_wav(self, duration_sec: float = 0.2, sample_rate: Optional[int] = None) -> bytes:
        rate = sample_rate or self.config.TTS_SAMPLE_RATE
        num_samples = int(rate * duration_sec)
        data_bytes = b"\x00\x00" * num_samples
        data_size = len(data_bytes)
        chunk_size = 36 + data_size
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            chunk_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            1,
            rate,
            rate * 2,
            2,
            16,
            b"data",
            data_size,
        )
        return header + data_bytes

    def synthesize_mock(self, text: str) -> bytes:
        cached = self.get_cached_audio(text, engine="mock")
        if cached:
            return cached
        duration = max(0.1, min(3.0, len(text.split()) * 0.15))
        wav_bytes = self.generate_mock_wav(duration_sec=duration)
        self.cache_audio(text, wav_bytes, engine="mock")
        return wav_bytes

    def play_audio_mock(self, audio_bytes: bytes, stop_event: Optional[threading.Event] = None) -> bool:
        self.set_state(AudioOutputState.PLAYING)
        duration = min(0.3, len(audio_bytes) / (self.config.TTS_SAMPLE_RATE * 2))
        start = time.time()
        while time.time() - start < duration:
            if stop_event and stop_event.is_set():
                self.set_state(AudioOutputState.IDLE)
                return False
            time.sleep(0.02)
        self.set_state(AudioOutputState.IDLE)
        return True

    def is_espeak_available(self) -> bool:
        return bool(shutil.which("espeak-ng") or shutil.which("espeak"))

    def synthesize_espeak(self, text: str) -> bytes:
        cached = self.get_cached_audio(text, engine="espeak")
        if cached:
            return cached
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            raise RuntimeError("espeak binary not found on system PATH")
        output_path = self.get_cache_path(text, engine="espeak")
        cmd = [binary, "-v", self.config.ESPEAK_VOICE, "-w", str(output_path), text]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10.0, check=False)
            if proc.returncode != 0 or not output_path.is_file():
                raise RuntimeError(f"espeak synthesis failed with code {proc.returncode}: {proc.stderr.decode(errors='ignore')}")
            return output_path.read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("espeak synthesis timed out") from exc

    def is_piper_available(self) -> bool:
        binary_ok = bool(shutil.which(self.config.PIPER_BINARY_PATH) or Path(self.config.PIPER_BINARY_PATH).is_file())
        model_ok = Path(self.config.PIPER_MODEL_PATH).is_file()
        return binary_ok and model_ok

    def synthesize_piper(self, text: str) -> bytes:
        cached = self.get_cached_audio(text, engine="piper")
        if cached:
            return cached
        binary = shutil.which(self.config.PIPER_BINARY_PATH) or self.config.PIPER_BINARY_PATH
        model_path = Path(self.config.PIPER_MODEL_PATH)
        if not (shutil.which(str(binary)) or Path(str(binary)).is_file()):
            raise RuntimeError(f"piper binary not found at {binary}")
        if not model_path.is_file():
            raise RuntimeError(f"piper onnx model not found at {model_path}")
        output_path = self.get_cache_path(text, engine="piper")
        cmd = [
            str(binary),
            "--model",
            str(model_path),
            "--output_file",
            str(output_path),
        ]
        if self.config.PIPER_SPEAKER_ID is not None and self.config.PIPER_SPEAKER_ID > 0:
            cmd.extend(["--speaker", str(self.config.PIPER_SPEAKER_ID)])
        try:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15.0,
                check=False,
            )
            if proc.returncode != 0 or not output_path.is_file():
                raise RuntimeError(
                    f"piper synthesis failed with code {proc.returncode}: {proc.stderr.decode(errors='ignore')}"
                )
            return output_path.read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("piper synthesis timed out") from exc
