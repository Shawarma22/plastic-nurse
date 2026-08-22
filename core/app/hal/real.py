from typing import Dict, Any, Tuple
import time
import cv2
from app.hal.base import BaseMotorController, BaseDoorActuator, BaseCameraDevice
from app.config import settings

class GpiozeroMotorController(BaseMotorController):
    def __init__(self) -> None:
        from gpiozero import Motor
        self.motor_left = Motor(
            forward=settings.PIN_MOTOR_L_FWD,
            backward=settings.PIN_MOTOR_L_BWD,
            enable=settings.PIN_MOTOR_L_PWM,
            pwm=True
        )
        self.motor_right = Motor(
            forward=settings.PIN_MOTOR_R_FWD,
            backward=settings.PIN_MOTOR_R_BWD,
            enable=settings.PIN_MOTOR_R_PWM,
            pwm=True
        )
        self.last_command_time = time.time()

    async def set_motors(self, left_speed: float, right_speed: float) -> None:
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))

        if left_speed > 0:
            self.motor_left.forward(left_speed)
        elif left_speed < 0:
            self.motor_left.backward(abs(left_speed))
        else:
            self.motor_left.stop()

        if right_speed > 0:
            self.motor_right.forward(right_speed)
        elif right_speed < 0:
            self.motor_right.backward(abs(right_speed))
        else:
            self.motor_right.stop()

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
        self.motor_left.stop()
        self.motor_right.stop()
        self.last_command_time = time.time()

    def get_state(self) -> Dict[str, Any]:
        return {
            "mode": "real_gpiozero",
            "left_value": self.motor_left.value,
            "right_value": self.motor_right.value,
            "last_command_time": self.last_command_time,
            "is_moving": self.motor_left.is_active or self.motor_right.is_active
        }

class GpiozeroDoorActuator(BaseDoorActuator):
    def __init__(self) -> None:
        from gpiozero import DigitalOutputDevice, DigitalInputDevice
        self.pin_open = DigitalOutputDevice(settings.PIN_DOOR_OPEN)
        self.pin_close = DigitalOutputDevice(settings.PIN_DOOR_CLOSE)
        self.limit_open = DigitalInputDevice(settings.PIN_DOOR_LIMIT_OPEN, pull_up=True)
        self.limit_close = DigitalInputDevice(settings.PIN_DOOR_LIMIT_CLOSED, pull_up=True)

    async def start_open(self) -> None:
        self.pin_close.off()
        self.pin_open.on()

    async def start_close(self) -> None:
        self.pin_open.off()
        self.pin_close.on()

    async def stop(self) -> None:
        self.pin_open.off()
        self.pin_close.off()

    async def is_open_limit_reached(self) -> bool:
        return self.limit_open.is_active

    async def is_close_limit_reached(self) -> bool:
        return self.limit_close.is_active

    def get_state(self) -> Dict[str, Any]:
        return {
            "mode": "real_gpiozero",
            "pin_open_active": self.pin_open.is_active,
            "pin_close_active": self.pin_close.is_active,
            "limit_open_active": self.limit_open.is_active,
            "limit_close_active": self.limit_close.is_active
        }

class Picamera2CameraDevice(BaseCameraDevice):
    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.cap = None

    def open(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            return self.cap.isOpened()
        except Exception:
            return False

    def close(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None

    def read_frame(self) -> Tuple[bool, bytes]:
        if not self.cap or not self.cap.isOpened():
            return False, b""
        ret, frame = self.cap.read()
        if not ret:
            return False, b""
        success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not success:
            return False, b""
        return True, buffer.tobytes()
