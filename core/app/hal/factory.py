from app.config import settings
from app.hal.base import BaseMotorController, BaseDoorActuator, BaseCameraDevice
from app.hal.mock import MockMotorController, MockDoorActuator, MockCameraDevice
from app.logger import logger

_motor_controller: BaseMotorController | None = None
_door_actuator: BaseDoorActuator | None = None
_camera_device: BaseCameraDevice | None = None

def get_motor_controller() -> BaseMotorController:
    global _motor_controller
    if _motor_controller is None:
        if settings.DROID_HAL == "real":
            try:
                from app.hal.real import GpiozeroMotorController
                _motor_controller = GpiozeroMotorController()
                logger.info("Initialized real GPIO motor controller")
            except Exception as e:
                logger.warning(f"Failed to initialize real motor controller: {e}. Falling back to mock.")
                _motor_controller = MockMotorController()
        else:
            _motor_controller = MockMotorController()
            logger.info("Initialized mock motor controller")
    return _motor_controller

def get_door_actuator() -> BaseDoorActuator:
    global _door_actuator
    if _door_actuator is None:
        if settings.DROID_HAL == "real":
            try:
                from app.hal.real import GpiozeroDoorActuator
                _door_actuator = GpiozeroDoorActuator()
                logger.info("Initialized real GPIO door actuator")
            except Exception as e:
                logger.warning(f"Failed to initialize real door actuator: {e}. Falling back to mock.")
                _door_actuator = MockDoorActuator()
        else:
            _door_actuator = MockDoorActuator()
            logger.info("Initialized mock door actuator")
    return _door_actuator

def get_camera_device() -> BaseCameraDevice:
    global _camera_device
    if _camera_device is None:
        if settings.DROID_HAL == "real":
            try:
                from app.hal.real import Picamera2CameraDevice
                cam = Picamera2CameraDevice(width=settings.CAMERA_WIDTH, height=settings.CAMERA_HEIGHT)
                if cam.open():
                    _camera_device = cam
                    logger.info("Initialized real camera device")
                else:
                    logger.warning("Real camera could not be opened. Falling back to mock.")
                    _camera_device = MockCameraDevice(width=settings.CAMERA_WIDTH, height=settings.CAMERA_HEIGHT)
                    _camera_device.open()
            except Exception as e:
                logger.warning(f"Failed to load real camera device: {e}. Falling back to mock.")
                _camera_device = MockCameraDevice(width=settings.CAMERA_WIDTH, height=settings.CAMERA_HEIGHT)
                _camera_device.open()
        else:
            _camera_device = MockCameraDevice(width=settings.CAMERA_WIDTH, height=settings.CAMERA_HEIGHT)
            _camera_device.open()
            logger.info("Initialized mock camera device")
    return _camera_device
