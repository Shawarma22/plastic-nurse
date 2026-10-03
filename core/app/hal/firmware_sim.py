import json
import math
import time
from typing import Dict, Any, Iterator


class FirmwareSimulator:
    def __init__(self, sample_rate_hz: int = 50, initial_battery_mv: int = 4100):
        self.sample_rate_hz = sample_rate_hz
        self.battery_mv = initial_battery_mv
        self.seq = 0
        self.start_time = time.monotonic()
        self.base_bpm = 72.0
        self.base_spo2 = 98.5

    def generate_packet(self) -> Dict[str, Any]:
        self.seq += 1
        elapsed = time.monotonic() - self.start_time
        ts_ms = int(elapsed * 1000)

        phase = elapsed * 2.0 * math.pi * (self.base_bpm / 60.0)
        qrs = math.exp(-((math.sin(phase / 2.0) * 10.0) ** 2)) * 1200.0
        ecg_val = int(2048 + 300 * math.sin(phase) + qrs)
        ecg_val = max(0, min(4095, ecg_val))

        ppg_wave = math.sin(phase) * 0.5 + 0.5
        ir_raw = int(250000 + 15000 * ppg_wave)
        red_raw = int(240000 + 12000 * ppg_wave)

        self.battery_mv = max(3300, self.battery_mv - (self.seq % 50 == 0))

        status = 0x01 | 0x02 | 0x04

        return {
            "seq": self.seq,
            "ts": ts_ms,
            "ppg": {
                "ir": ir_raw,
                "red": red_raw,
                "bpm": round(self.base_bpm + math.sin(elapsed * 0.1) * 2.0, 1),
                "spo2": round(self.base_spo2 + math.cos(elapsed * 0.05) * 0.5, 1),
                "conf": 0.96,
                "finger": True,
            },
            "ecg": {
                "raw": ecg_val,
                "lead_off": False,
            },
            "bat": self.battery_mv,
            "status": status,
        }

    def serialize_packet(self, packet: Dict[str, Any]) -> str:
        return json.dumps(packet, separators=(",", ":"))

    def stream_packets(self, count: int = 10, interval_s: float = 0.02) -> Iterator[str]:
        for _ in range(count):
            packet = self.generate_packet()
            yield self.serialize_packet(packet)
            if interval_s > 0:
                time.sleep(interval_s)
