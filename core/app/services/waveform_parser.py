import struct
from typing import Optional, Dict, Any, List

HEADER_FORMAT = "<BBHIIHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
SAMPLE_FORMAT = "<HIIB"
SAMPLE_SIZE = struct.calcsize(SAMPLE_FORMAT)

WAVEFORM_MAGIC_0 = 0xAA
WAVEFORM_MAGIC_1 = 0x55
WAVEFORM_BATCH_VERSION = 1


class WaveformBatchParser:
    @staticmethod
    def unpack(data: bytes) -> Optional[Dict[str, Any]]:
        if not data or len(data) < HEADER_SIZE:
            return None

        magic0, magic1, version, batch_seq, start_ts, sample_interval, sample_count = struct.unpack_from(
            HEADER_FORMAT, data, 0
        )

        if magic0 != WAVEFORM_MAGIC_0 or magic1 != WAVEFORM_MAGIC_1 or version != WAVEFORM_BATCH_VERSION:
            return None

        expected_size = HEADER_SIZE + (sample_count * SAMPLE_SIZE)
        if len(data) < expected_size:
            return None

        samples: List[Dict[str, Any]] = []
        offset = HEADER_SIZE
        for _ in range(sample_count):
            ecg_raw, ir_raw, red_raw, flags = struct.unpack_from(SAMPLE_FORMAT, data, offset)
            samples.append({
                "ecg_raw": ecg_raw,
                "ir_raw": ir_raw,
                "red_raw": red_raw,
                "flags": flags,
            })
            offset += SAMPLE_SIZE

        return {
            "version": version,
            "batch_seq": batch_seq,
            "start_timestamp_ms": start_ts,
            "sample_interval_ms": sample_interval,
            "sample_count": sample_count,
            "samples": samples,
            "raw_bytes": data[:expected_size],
        }

    @staticmethod
    def pack(
        batch_seq: int,
        start_ts_ms: int,
        sample_interval_ms: int,
        samples: List[Dict[str, Any]],
    ) -> bytes:
        sample_count = len(samples)
        header = struct.pack(
            HEADER_FORMAT,
            WAVEFORM_MAGIC_0,
            WAVEFORM_MAGIC_1,
            WAVEFORM_BATCH_VERSION,
            batch_seq,
            start_ts_ms,
            sample_interval_ms,
            sample_count,
        )
        sample_bytes = bytearray()
        for s in samples:
            sample_bytes.extend(
                struct.pack(
                    SAMPLE_FORMAT,
                    int(s.get("ecg_raw", 0)),
                    int(s.get("ir_raw", 0)),
                    int(s.get("red_raw", 0)),
                    int(s.get("flags", 0)),
                )
            )
        return bytes(header + sample_bytes)
