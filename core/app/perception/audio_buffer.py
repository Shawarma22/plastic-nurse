from typing import Optional

class AudioRingBuffer:
    def __init__(self, capacity_bytes: int = 96000) -> None:
        self.capacity = max(1024, capacity_bytes)
        self._buffer = bytearray(self.capacity)
        self._write_pos = 0
        self._size = 0

    def write(self, data: bytes) -> None:
        if not data:
            return
        data_len = len(data)
        if data_len >= self.capacity:
            self._buffer[:] = data[-self.capacity:]
            self._write_pos = 0
            self._size = self.capacity
            return

        space_at_end = self.capacity - self._write_pos
        if data_len <= space_at_end:
            self._buffer[self._write_pos : self._write_pos + data_len] = data
            self._write_pos = (self._write_pos + data_len) % self.capacity
        else:
            self._buffer[self._write_pos : self.capacity] = data[:space_at_end]
            remainder = data_len - space_at_end
            self._buffer[0:remainder] = data[space_at_end:]
            self._write_pos = remainder

        self._size = min(self.capacity, self._size + data_len)

    def read_recent(self, num_bytes: Optional[int] = None) -> bytes:
        if self._size == 0:
            return b""
        requested = min(self._size, num_bytes) if num_bytes is not None else self._size
        start_idx = (self._write_pos - requested) % self.capacity
        if start_idx + requested <= self.capacity:
            return bytes(self._buffer[start_idx : start_idx + requested])
        part1 = self._buffer[start_idx : self.capacity]
        part2 = self._buffer[0 : requested - len(part1)]
        return bytes(part1 + part2)

    def read_all(self) -> bytes:
        return self.read_recent(self._size)

    def clear(self) -> None:
        self._write_pos = 0
        self._size = 0

    def size(self) -> int:
        return self._size

    def is_full(self) -> bool:
        return self._size >= self.capacity
