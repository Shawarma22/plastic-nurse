import argparse
import json
import math
import random
import sys
import time
from typing import Dict, Any, Iterator


class FirmwareSimulator:
    def __init__(
        self,
        sample_rate_hz: int = 50,
        initial_battery_mv: int = 4100,
        drop_rate: float = 0.0,
        disconnect_ppg: bool = False,
        disconnect_ecg: bool = False,
    ):
        self.sample_rate_hz = sample_rate_hz
        self.battery_mv = initial_battery_mv
        self.drop_rate = max(0.0, min(1.0, drop_rate))
        self.disconnect_ppg = disconnect_ppg
        self.disconnect_ecg = disconnect_ecg
        self.seq = 0
        self.start_time = time.monotonic()
        self.base_bpm = 72.0
        self.base_spo2 = 98.5

    def generate_packet(self) -> Dict[str, Any]:
        self.seq += 1
        elapsed = time.monotonic() - self.start_time
        ts_ms = int(elapsed * 1000)

        phase = elapsed * 2.0 * math.pi * (self.base_bpm / 60.0)

        if self.disconnect_ecg:
            ecg_val = 0
            lead_off = True
        else:
            qrs = math.exp(-((math.sin(phase / 2.0) * 10.0) ** 2)) * 1200.0
            ecg_val = int(2048 + 300 * math.sin(phase) + qrs)
            ecg_val = max(0, min(4095, ecg_val))
            lead_off = False

        if self.disconnect_ppg:
            ir_raw = 0
            red_raw = 0
            bpm = 0.0
            spo2 = 0.0
            conf = 0.0
            finger = False
        else:
            ppg_wave = math.sin(phase) * 0.5 + 0.5
            ir_raw = int(250000 + 15000 * ppg_wave)
            red_raw = int(240000 + 12000 * ppg_wave)
            bpm = round(self.base_bpm + math.sin(elapsed * 0.1) * 2.0, 1)
            spo2 = round(self.base_spo2 + math.cos(elapsed * 0.05) * 0.5, 1)
            conf = 0.96
            finger = True

        self.battery_mv = max(3300, self.battery_mv - (self.seq % 50 == 0))

        status = 0x00
        if not self.disconnect_ppg:
            status |= 0x01 | 0x04
        if not self.disconnect_ecg:
            status |= 0x02
        else:
            status |= 0x08

        return {
            "seq": self.seq,
            "ts": ts_ms,
            "ppg": {
                "ir": ir_raw,
                "red": red_raw,
                "bpm": bpm,
                "spo2": spo2,
                "conf": conf,
                "finger": finger,
            },
            "ecg": {
                "raw": ecg_val,
                "lead_off": lead_off,
            },
            "bat": self.battery_mv,
            "status": status,
        }

    def serialize_packet(self, packet: Dict[str, Any]) -> str:
        return json.dumps(packet, separators=(",", ":"))

    def stream_packets(self, count: int = 10, interval_s: float = 0.02) -> Iterator[str]:
        for _ in range(count):
            packet = self.generate_packet()
            if self.drop_rate > 0.0 and random.random() < self.drop_rate:
                continue
            yield self.serialize_packet(packet)
            if interval_s > 0:
                time.sleep(interval_s)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--count", type=int, default=100)
    parser.add_argument("--rate", type=int, default=50)
    parser.add_argument("--drop-rate", type=float, default=0.0)
    parser.add_argument("--disconnect-ppg", action="store_true")
    parser.add_argument("--disconnect-ecg", action="store_true")
    args = parser.parse_args()

    interval = 1.0 / max(1, args.rate)
    sim = FirmwareSimulator(
        sample_rate_hz=args.rate,
        drop_rate=args.drop_rate,
        disconnect_ppg=args.disconnect_ppg,
        disconnect_ecg=args.disconnect_ecg,
    )

    try:
        for line in sim.stream_packets(count=args.count, interval_s=interval):
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
