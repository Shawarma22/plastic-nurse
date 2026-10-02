import math
import struct

class EnergyVAD:
    def __init__(self, threshold: float = 500.0, sample_rate: int = 16000) -> None:
        self.threshold = max(0.0, float(threshold))
        self.sample_rate = sample_rate

    def calculate_rms(self, chunk: bytes) -> float:
        if not chunk or len(chunk) < 2:
            return 0.0
        count = len(chunk) // 2
        try:
            samples = struct.unpack(f"<{count}h", chunk[: count * 2])
            sum_sq = sum(float(s) * float(s) for s in samples)
            mean_sq = sum_sq / count
            return math.sqrt(mean_sq)
        except Exception:
            return 0.0

    def is_speech(self, chunk: bytes) -> bool:
        rms = self.calculate_rms(chunk)
        return rms >= self.threshold

    def set_threshold(self, threshold: float) -> None:
        self.threshold = max(0.0, float(threshold))

    def get_threshold(self) -> float:
        return self.threshold
