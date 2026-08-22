import asyncio
from enum import Enum
from typing import Dict, Any, Optional
from app.hal.base import BaseDoorActuator
from app.hal.factory import get_door_actuator
from app.logger import logger

class DoorState(str, Enum):
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    ERROR = "error"

class DoorService:
    def __init__(self, actuator: Optional[BaseDoorActuator] = None) -> None:
        self.actuator: BaseDoorActuator = actuator or get_door_actuator()
        self.state: DoorState = DoorState.CLOSED
        self._transition_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def open_door(self) -> Dict[str, Any]:
        async with self._lock:
            if self.state in (DoorState.OPEN, DoorState.OPENING):
                return self.get_status()
            if self._transition_task and not self._transition_task.done():
                self._transition_task.cancel()
            self.state = DoorState.OPENING
            self._transition_task = asyncio.create_task(self._run_open_cycle())
            return self.get_status()

    async def close_door(self) -> Dict[str, Any]:
        async with self._lock:
            if self.state in (DoorState.CLOSED, DoorState.CLOSING):
                return self.get_status()
            if self._transition_task and not self._transition_task.done():
                self._transition_task.cancel()
            self.state = DoorState.CLOSING
            self._transition_task = asyncio.create_task(self._run_close_cycle())
            return self.get_status()

    async def stop(self) -> Dict[str, Any]:
        async with self._lock:
            if self._transition_task and not self._transition_task.done():
                self._transition_task.cancel()
            await self.actuator.stop()
            if self.state == DoorState.OPENING:
                self.state = DoorState.OPEN
            elif self.state == DoorState.CLOSING:
                self.state = DoorState.CLOSED
            return self.get_status()

    async def _run_open_cycle(self) -> None:
        try:
            await self.actuator.start_open()
            elapsed = 0.0
            timeout = 3.0
            step = 0.1
            while elapsed < timeout:
                await asyncio.sleep(step)
                elapsed += step
                if await self.actuator.is_open_limit_reached():
                    break
            await self.actuator.stop()
            self.state = DoorState.OPEN
            logger.info("Door reached OPEN state")
        except asyncio.CancelledError:
            await self.actuator.stop()
        except Exception as e:
            logger.error(f"Door open failure: {e}")
            await self.actuator.stop()
            self.state = DoorState.ERROR

    async def _run_close_cycle(self) -> None:
        try:
            await self.actuator.start_close()
            elapsed = 0.0
            timeout = 3.0
            step = 0.1
            while elapsed < timeout:
                await asyncio.sleep(step)
                elapsed += step
                if await self.actuator.is_close_limit_reached():
                    break
            await self.actuator.stop()
            self.state = DoorState.CLOSED
            logger.info("Door reached CLOSED state")
        except asyncio.CancelledError:
            await self.actuator.stop()
        except Exception as e:
            logger.error(f"Door close failure: {e}")
            await self.actuator.stop()
            self.state = DoorState.ERROR

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "actuator": self.actuator.get_state()
        }

door_service = DoorService()
