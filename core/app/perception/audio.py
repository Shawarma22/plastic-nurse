from abc import ABC, abstractmethod
import math
import struct
from typing import Optional, List

class BaseAudioSource(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def read_chunk(self, chunk_size: int = 4096) -> bytes:
        pass

class MockAudioSource(BaseAudioSource):
    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self.is_active = False
        self._canned_phrases: List[str] = []
        self._phase = 0.0

    def start(self) -> None:
        self.is_active = True

    def stop(self) -> None:
        self.is_active = False

    def feed_phrase(self, phrase: str) -> None:
        self._canned_phrases.append(phrase)

    def pop_phrase(self) -> Optional[str]:
        if self._canned_phrases:
            return self._canned_phrases.pop(0)
        return None

    def read_chunk(self, chunk_size: int = 4096) -> bytes:
        if not self.is_active:
            return b""
        num_samples = chunk_size // 2
        frequency = 440.0
        samples = []
        for _ in range(num_samples):
            val = int(32767.0 * 0.1 * math.sin(self._phase))
            samples.append(val)
            self._phase += 2.0 * math.pi * frequency / self.sample_rate
            if self._phase > 2.0 * math.pi:
                self._phase -= 2.0 * math.pi
        return struct.pack(f"<{len(samples)}h", *samples)
