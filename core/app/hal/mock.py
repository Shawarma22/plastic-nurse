import time
from typing import Dict, Any, Tuple
import numpy as np
import cv2
from app.hal.base import BaseMotorController, BaseDoorActuator, BaseCameraDevice

class MockMotorController(BaseMotorController):
    def __init__(self) -> None:
        self.left_speed: float = 0.0
        self.right_speed: float = 0.0
        self.last_command_time: float = time.time()

    async def set_motors(self, left_speed: float, right_speed: float) -> None:
        self.left_speed = max(-1.0, min(1.0, left_speed))
        self.right_speed = max(-1.0, min(1.0, right_speed))
        self.last_command_time = time.time()

    async def forward(self, speed: float = 1.0) -> None:
        await self.set_motors(speed, speed)

    async def backward(self, speed: float = 1.0) -> None:
        await self.set_motors(-speed, -speed)

    async def turn_left(self, speed: float = 1.0) -> None:
        await self.set_motors(-speed, speed)

    async def turn_right(self, speed: float = 1.0) -> None:
        await self.set_motors(speed, -speed)

    async def stop(self) -> None:
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.last_command_time = time.time()

    def get_state(self) -> Dict[str, Any]:
        return {
            "mode": "mock",
            "left_speed": self.left_speed,
            "right_speed": self.right_speed,
            "last_command_time": self.last_command_time,
            "is_moving": self.left_speed != 0.0 or self.right_speed != 0.0
        }

class MockDoorActuator(BaseDoorActuator):
    def __init__(self) -> None:
        self.is_moving_open: bool = False
        self.is_moving_close: bool = False
        self.position: float = 0.0
        self.last_update: float = time.time()

    def _update_position(self) -> None:
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now
        if self.is_moving_open:
            self.position = min(1.0, self.position + elapsed * 1.0)
        elif self.is_moving_close:
            self.position = max(0.0, self.position - elapsed * 1.0)

    async def start_open(self) -> None:
        self._update_position()
        self.is_moving_open = True
        self.is_moving_close = False

    async def start_close(self) -> None:
        self._update_position()
        self.is_moving_open = False
        self.is_moving_close = True

    async def stop(self) -> None:
        self._update_position()
        self.is_moving_open = False
        self.is_moving_close = False

    async def is_open_limit_reached(self) -> bool:
        self._update_position()
        return self.position >= 1.0

    async def is_close_limit_reached(self) -> bool:
        self._update_position()
        return self.position <= 0.0

    def get_state(self) -> Dict[str, Any]:
        self._update_position()
        return {
            "mode": "mock",
            "position": round(self.position, 2),
            "is_moving_open": self.is_moving_open,
            "is_moving_close": self.is_moving_close
        }

class MockCameraDevice(BaseCameraDevice):
    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.is_opened = False
        self.frame_count = 0
        self._cached_frame: bytes = b""
        self._generate_cached_frame()

    def _generate_cached_frame(self) -> None:
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:, :] = (30, 30, 40)
        cv2.putText(
            img,
            "DROID MOCK CAMERA",
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 200),
            2
        )
        cv2.rectangle(
            img,
            (50, 100),
            (self.width - 50, self.height - 50),
            (0, 140, 255),
            2
        )
        success, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if success:
            self._cached_frame = buffer.tobytes()

    def open(self) -> bool:
        self.is_opened = True
        if not self._cached_frame:
            self._generate_cached_frame()
        return True

    def close(self) -> None:
        self.is_opened = False

    def read_frame(self) -> Tuple[bool, bytes]:
        if not self.is_opened:
            return False, b""
        self.frame_count += 1
        return True, self._cached_frame
