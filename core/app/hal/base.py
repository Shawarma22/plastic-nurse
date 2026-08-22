from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class BaseMotorController(ABC):
    @abstractmethod
    async def set_motors(self, left_speed: float, right_speed: float) -> None:
        pass

    @abstractmethod
    async def forward(self, speed: float = 1.0) -> None:
        pass

    @abstractmethod
    async def backward(self, speed: float = 1.0) -> None:
        pass

    @abstractmethod
    async def turn_left(self, speed: float = 1.0) -> None:
        pass

    @abstractmethod
    async def turn_right(self, speed: float = 1.0) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        pass

class BaseDoorActuator(ABC):
    @abstractmethod
    async def start_open(self) -> None:
        pass

    @abstractmethod
    async def start_close(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def is_open_limit_reached(self) -> bool:
        pass

    @abstractmethod
    async def is_close_limit_reached(self) -> bool:
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        pass

class BaseCameraDevice(ABC):
    @abstractmethod
    def open(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, bytes]:
        pass
