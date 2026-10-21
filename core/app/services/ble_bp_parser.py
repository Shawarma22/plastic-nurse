import struct
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def parse_sfloat(raw: int) -> Optional[float]:
    if raw in (0x07FF, 0x0800, 0x0801):
        return None
    if raw == 0x07FE:
        return float("inf")
    if raw == 0x0802:
        return float("-inf")
    mantissa = raw & 0x0FFF
    if mantissa >= 0x0800:
        mantissa -= 0x1000
    exponent = (raw >> 12) & 0x0F
    if exponent >= 0x08:
        exponent -= 0x10
    return float(mantissa * (10 ** exponent))


def pack_sfloat(val: float, exponent: int = 0) -> int:
    mantissa = int(round(val / (10 ** exponent)))
    if mantissa < 0:
        mantissa = (1 << 12) + mantissa
    exp_signed = exponent if exponent >= 0 else (1 << 4) + exponent
    return ((exp_signed & 0x0F) << 12) | (mantissa & 0x0FFF)


class BleBloodPressureParser:
    FLAG_UNIT_KPA = 0x01
    FLAG_TIMESTAMP_PRESENT = 0x02
    FLAG_PULSE_RATE_PRESENT = 0x04
    FLAG_USER_ID_PRESENT = 0x08
    FLAG_STATUS_PRESENT = 0x10

    @classmethod
    def unpack(cls, data: bytes) -> Optional[Dict[str, Any]]:
        if not data or len(data) < 7:
            return None
        flags = data[0]
        unit = "kPa" if (flags & cls.FLAG_UNIT_KPA) else "mmHg"

        sys_raw, dia_raw, map_raw = struct.unpack_from("<HHH", data, 1)
        systolic = parse_sfloat(sys_raw)
        diastolic = parse_sfloat(dia_raw)
        mean_arterial_pressure = parse_sfloat(map_raw)

        if systolic is None or diastolic is None:
            return None

        offset = 7
        ts_val: Optional[datetime] = None
        if flags & cls.FLAG_TIMESTAMP_PRESENT:
            if len(data) < offset + 7:
                return None
            year, month, day, hour, minute, second = struct.unpack_from("<HBBBBB", data, offset)
            try:
                ts_val = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            except Exception:
                ts_val = None
            offset += 7

        pulse_rate: Optional[float] = None
        if flags & cls.FLAG_PULSE_RATE_PRESENT:
            if len(data) < offset + 2:
                return None
            pr_raw = struct.unpack_from("<H", data, offset)[0]
            pulse_rate = parse_sfloat(pr_raw)
            offset += 2

        user_id: Optional[int] = None
        if flags & cls.FLAG_USER_ID_PRESENT:
            if len(data) < offset + 1:
                return None
            user_id = data[offset]
            offset += 1

        status_flags: Optional[int] = None
        if flags & cls.FLAG_STATUS_PRESENT:
            if len(data) < offset + 2:
                return None
            status_flags = struct.unpack_from("<H", data, offset)[0]
            offset += 2

        return {
            "systolic": systolic,
            "diastolic": diastolic,
            "mean_arterial_pressure": mean_arterial_pressure,
            "pulse_rate": pulse_rate,
            "unit": unit,
            "timestamp": ts_val or datetime.now(timezone.utc),
            "user_id": user_id,
            "status_flags": status_flags,
        }

    @classmethod
    def pack(
        cls,
        systolic: float,
        diastolic: float,
        mean_arterial_pressure: float,
        pulse_rate: Optional[float] = None,
        unit: str = "mmHg",
        dt: Optional[datetime] = None,
        user_id: Optional[int] = None,
        status_flags: Optional[int] = None,
    ) -> bytes:
        flags = 0
        if unit == "kPa":
            flags |= cls.FLAG_UNIT_KPA
        if dt is not None:
            flags |= cls.FLAG_TIMESTAMP_PRESENT
        if pulse_rate is not None:
            flags |= cls.FLAG_PULSE_RATE_PRESENT
        if user_id is not None:
            flags |= cls.FLAG_USER_ID_PRESENT
        if status_flags is not None:
            flags |= cls.FLAG_STATUS_PRESENT

        sys_sfloat = pack_sfloat(systolic, 0)
        dia_sfloat = pack_sfloat(diastolic, 0)
        map_sfloat = pack_sfloat(mean_arterial_pressure, 0)

        buf = bytearray(struct.pack("<BHHH", flags, sys_sfloat, dia_sfloat, map_sfloat))

        if dt is not None:
            buf.extend(struct.pack("<HBBBBB", dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))

        if pulse_rate is not None:
            pr_sfloat = pack_sfloat(pulse_rate, 0)
            buf.extend(struct.pack("<H", pr_sfloat))

        if user_id is not None:
            buf.append(user_id & 0xFF)

        if status_flags is not None:
            buf.extend(struct.pack("<H", status_flags))

        return bytes(buf)
