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
        include_temp: bool = False,
        include_dispenser: bool = False,
        disconnect_temp: bool = False,
        target_temp_present: bool = True,
        base_ambient_c: float = 24.5,
        base_object_c: float = 36.8,
        initial_compartment: int = 0,
    ):
        self.sample_rate_hz = sample_rate_hz
        self.battery_mv = initial_battery_mv
        self.drop_rate = max(0.0, min(1.0, drop_rate))
        self.disconnect_ppg = disconnect_ppg
        self.disconnect_ecg = disconnect_ecg
        self.include_temp = include_temp
        self.include_dispenser = include_dispenser
        self.disconnect_temp = disconnect_temp
        self.target_temp_present = target_temp_present
        self.base_ambient_c = base_ambient_c
        self.base_object_c = base_object_c
        self.current_compartment = initial_compartment
        self.target_compartment = initial_compartment
        self.dispenser_moving = False
        self.dispenser_homed = True
        self.dispenser_stalled = False
        self.seq = 0
        self.start_time = time.monotonic()
        self.base_bpm = 72.0
        self.base_spo2 = 98.5

    def move_to_compartment(self, comp: int) -> bool:
        if comp < 0 or comp >= 14:
            return False
        self.target_compartment = comp
        self.current_compartment = comp
        self.dispenser_moving = False
        return True

    def home_dispenser(self) -> None:
        self.current_compartment = 0
        self.target_compartment = 0
        self.dispenser_homed = True
        self.dispenser_moving = False
        self.dispenser_stalled = False

    def trigger_stall(self) -> None:
        self.dispenser_stalled = True
        self.dispenser_moving = False

    def clear_stall(self) -> None:
        self.dispenser_stalled = False

    def generate_ecg_sample(self, elapsed: float) -> int:
        phase = elapsed * 2.0 * math.pi * (self.base_bpm / 60.0)
        cycle_phase = (phase % (2.0 * math.pi)) - math.pi
        p_wave = 140.0 * math.exp(-((cycle_phase + 1.2) / 0.18) ** 2)
        q_wave = -180.0 * math.exp(-((cycle_phase + 0.35) / 0.08) ** 2)
        r_wave = 1500.0 * math.exp(-((cycle_phase) / 0.1) ** 2)
        s_wave = -320.0 * math.exp(-((cycle_phase - 0.35) / 0.09) ** 2)
        t_wave = 280.0 * math.exp(-((cycle_phase - 1.2) / 0.35) ** 2)
        baseline = 2048.0 + 35.0 * math.sin(elapsed * 0.3 * 2.0 * math.pi)
        sample = int(baseline + p_wave + q_wave + r_wave + s_wave + t_wave)
        return max(0, min(4095, sample))

    def generate_packet(self) -> Dict[str, Any]:
        self.seq += 1
        elapsed = time.monotonic() - self.start_time
        ts_ms = int(elapsed * 1000)

        phase = elapsed * 2.0 * math.pi * (self.base_bpm / 60.0)

        if self.disconnect_ecg:
            ecg_val = 0
            lead_off = True
        else:
            ecg_val = self.generate_ecg_sample(elapsed)
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

        packet: Dict[str, Any] = {
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

        if self.include_temp:
            if self.disconnect_temp:
                temp_data = {
                    "amb": 0.0,
                    "obj": 0.0,
                    "conf": 0.0,
                    "target": False,
                }
            else:
                amb = round(self.base_ambient_c + 0.1 * math.sin(elapsed * 0.05), 2)
                if self.target_temp_present:
                    obj = round(self.base_object_c + 0.05 * math.sin(elapsed * 0.1), 2)
                    conf = 0.95
                    target = True
                    status |= 0x20 | 0x40
                else:
                    obj = round(self.base_ambient_c + 0.15 * math.cos(elapsed * 0.1), 2)
                    conf = 0.05
                    target = False
                    status |= 0x20
                temp_data = {
                    "amb": amb,
                    "obj": obj,
                    "conf": conf,
                    "target": target,
                }
            packet["temp"] = temp_data
            packet["status"] = status

        if self.include_dispenser:
            if self.dispenser_moving:
                status |= 0x80
                packet["status"] = status
            packet["dispenser"] = {
                "comp": self.current_compartment,
                "target": self.target_compartment,
                "moving": self.dispenser_moving,
                "homed": self.dispenser_homed,
                "stall": self.dispenser_stalled,
            }

        return packet

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
    parser.add_argument("--include-temp", action="store_true")
    parser.add_argument("--include-dispenser", action="store_true")
    parser.add_argument("--disconnect-temp", action="store_true")
    parser.add_argument("--no-target-temp", action="store_true")
    args = parser.parse_args()

    interval = 1.0 / max(1, args.rate)
    sim = FirmwareSimulator(
        sample_rate_hz=args.rate,
        drop_rate=args.drop_rate,
        disconnect_ppg=args.disconnect_ppg,
        disconnect_ecg=args.disconnect_ecg,
        include_temp=args.include_temp,
        include_dispenser=args.include_dispenser,
        disconnect_temp=args.disconnect_temp,
        target_temp_present=not args.no_target_temp,
    )

    try:
        for line in sim.stream_packets(count=args.count, interval_s=interval):
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
