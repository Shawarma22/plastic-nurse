import asyncio
import hashlib
import logging
import os
import queue
import re
import shutil
import struct
import subprocess
import time
from enum import Enum
from pathlib import Path
import threading
from typing import Dict, Any, List, Optional, Tuple
import uuid
from app.config import settings, Settings
from app.services.ws_manager import ws_manager

logger = logging.getLogger("droid.tts")


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
        self.fallback_count: int = 0
        self.last_used_engine: str = self.engine_type
        self.total_utterances: int = 0
        self.total_characters: int = 0
        self.total_audio_seconds: float = 0.0
        self.total_synthesis_time_ms: float = 0.0
        self.last_synthesis_time_ms: float = 0.0
        self._queue: queue.Queue[Tuple[str, str, Optional[str]]] = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker_event = threading.Event()
        self._interrupt_event = threading.Event()
        self._is_running: bool = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def _broadcast_tts_state(self) -> None:
        if self.loop and self.loop.is_running():
            payload = {
                "type": "tts_state",
                "state": self.state.value,
                "current_utterance_id": self.current_utterance_id,
                "queue_size": self._queue.qsize(),
                "engine": self.last_used_engine,
            }
            try:
                asyncio.run_coroutine_threadsafe(ws_manager.broadcast_state(payload), self.loop)
            except Exception:
                pass

    def get_state(self) -> AudioOutputState:
        with self._lock:
            return self.state

    def set_state(self, new_state: AudioOutputState) -> None:
        with self._lock:
            self.state = new_state
        self._broadcast_tts_state()

    def is_busy(self) -> bool:
        with self._lock:
            return self.state in (AudioOutputState.SYNTHESIZING, AudioOutputState.PLAYING) or not self._queue.empty()

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self.state.value,
                "current_utterance_id": self.current_utterance_id,
                "queue_size": self._queue.qsize(),
                "total_utterances": self.total_utterances,
                "total_characters": self.total_characters,
                "total_audio_seconds": round(self.total_audio_seconds, 2),
                "total_synthesis_time_ms": round(self.total_synthesis_time_ms, 2),
                "last_synthesis_time_ms": round(self.last_synthesis_time_ms, 2),
                "fallback_count": self.fallback_count,
                "engine_type": self.engine_type,
                "last_used_engine": self.last_used_engine,
                "is_piper_available": self.is_piper_available(),
                "is_espeak_available": self.is_espeak_available(),
            }

    def start(self) -> None:
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_worker_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def stop_worker(self) -> None:
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_worker_event.set()
            self._interrupt_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def stop(self) -> None:
        self._interrupt_event.set()
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except (queue.Empty, ValueError):
                    break
            self.current_utterance_id = None
            self.state = AudioOutputState.IDLE
        self._broadcast_tts_state()

    def cancel_utterance(self, utterance_id: str) -> bool:
        with self._lock:
            if self.current_utterance_id == utterance_id:
                self._interrupt_event.set()
                self.current_utterance_id = None
                self.state = AudioOutputState.IDLE
                self._broadcast_tts_state()
                return True
            items: List[Tuple[str, str, Optional[str]]] = []
            found = False
            while not self._queue.empty():
                try:
                    item = self._queue.get_nowait()
                    if item[0] == utterance_id:
                        found = True
                        self._queue.task_done()
                    else:
                        items.append(item)
                except queue.Empty:
                    break
            for rem in items:
                self._queue.put(rem)
            return found

    def enqueue_speech(self, text: str, engine: Optional[str] = None) -> str:
        utterance_id = str(uuid.uuid4())
        cleaned = self.clean_text(text)
        if not cleaned:
            return utterance_id
        self._queue.put((utterance_id, cleaned, engine))
        self._broadcast_tts_state()
        return utterance_id

    def _worker_loop(self) -> None:
        while not self._stop_worker_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            utterance_id, text, engine = item
            with self._lock:
                self.current_utterance_id = utterance_id
                self.total_utterances += 1
                self.total_characters += len(text)
            self._interrupt_event.clear()
            self._broadcast_tts_state()
            try:
                chunks = self.chunk_text(text)
                for chunk in chunks:
                    if self._interrupt_event.is_set() or self._stop_worker_event.is_set():
                        break
                    audio_bytes, _ = self.synthesize(chunk, preferred_engine=engine)
                    if self._interrupt_event.is_set() or self._stop_worker_event.is_set():
                        break
                    self.play_audio_mock(audio_bytes, stop_event=self._interrupt_event)
            except Exception as e:
                logger.error(f"Error processing utterance {utterance_id}: {e}")
                self.set_state(AudioOutputState.ERROR)
            finally:
                with self._lock:
                    self.current_utterance_id = None
                if self.get_state() != AudioOutputState.ERROR:
                    self.set_state(AudioOutputState.IDLE)
                self._queue.task_done()
                self._broadcast_tts_state()

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

    def synthesize(self, text: str, preferred_engine: Optional[str] = None) -> Tuple[bytes, str]:
        start_time = time.perf_counter()
        self.set_state(AudioOutputState.SYNTHESIZING)
        cleaned = self.clean_text(text)
        if not cleaned:
            self.set_state(AudioOutputState.IDLE)
            return b"", "none"
        engine = preferred_engine or self.engine_type
        data = b""
        used_engine = "mock"
        if engine == "piper":
            try:
                data = self.synthesize_piper(cleaned)
                used_engine = "piper"
            except Exception as e:
                logger.warning(f"Piper synthesis error: {e}, falling back to espeak")
                with self._lock:
                    self.fallback_count += 1
                engine = "espeak"
        if engine == "espeak":
            try:
                data = self.synthesize_espeak(cleaned)
                used_engine = "espeak"
            except Exception as e:
                logger.warning(f"Espeak synthesis error: {e}, falling back to mock")
                with self._lock:
                    self.fallback_count += 1
                engine = "mock"
        if not data:
            data = self.synthesize_mock(cleaned)
            used_engine = "mock"
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        with self._lock:
            self.last_used_engine = used_engine
            self.last_synthesis_time_ms = elapsed_ms
            self.total_synthesis_time_ms += elapsed_ms
            if len(data) > 44:
                pcm_len = len(data) - 44
                sec = pcm_len / (self.config.TTS_SAMPLE_RATE * 2)
                self.total_audio_seconds += sec
        self.set_state(AudioOutputState.IDLE)
        return data, used_engine


tts_service = TtsService()
