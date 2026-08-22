import asyncio
from typing import Dict, Any, Optional
from app.hal.base import BaseMotorController
from app.hal.factory import get_motor_controller
from app.config import settings
from app.logger import logger

class MotorService:
    def __init__(self, controller: Optional[BaseMotorController] = None, timeout_sec: Optional[float] = None) -> None:
        self.controller: BaseMotorController = controller or get_motor_controller()
        self.timeout_sec: float = timeout_sec if timeout_sec is not None else settings.MOTOR_WATCHDOG_TIMEOUT_SEC
        self._watchdog_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def _reset_watchdog(self) -> None:
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def _watchdog_loop(self) -> None:
        try:
            await asyncio.sleep(self.timeout_sec)
            async with self._lock:
                await self.controller.stop()
                logger.info("Motor watchdog auto-stop triggered after timeout")
        except asyncio.CancelledError:
            pass

    async def forward(self, speed: float = 1.0) -> Dict[str, Any]:
        async with self._lock:
            await self.controller.forward(speed)
            await self._reset_watchdog()
            return self.controller.get_state()

    async def backward(self, speed: float = 1.0) -> Dict[str, Any]:
        async with self._lock:
            await self.controller.backward(speed)
            await self._reset_watchdog()
            return self.controller.get_state()

    async def turn_left(self, speed: float = 1.0) -> Dict[str, Any]:
        async with self._lock:
            await self.controller.turn_left(speed)
            await self._reset_watchdog()
            return self.controller.get_state()

    async def turn_right(self, speed: float = 1.0) -> Dict[str, Any]:
        async with self._lock:
            await self.controller.turn_right(speed)
            await self._reset_watchdog()
            return self.controller.get_state()

    async def set_motors(self, left_speed: float, right_speed: float) -> Dict[str, Any]:
        async with self._lock:
            await self.controller.set_motors(left_speed, right_speed)
            await self._reset_watchdog()
            return self.controller.get_state()

    async def stop(self) -> Dict[str, Any]:
        async with self._lock:
            if self._watchdog_task and not self._watchdog_task.done():
                self._watchdog_task.cancel()
            await self.controller.stop()
            return self.controller.get_state()

    def get_status(self) -> Dict[str, Any]:
        state = self.controller.get_state()
        state["watchdog_timeout_sec"] = self.timeout_sec
        state["watchdog_active"] = self._watchdog_task is not None and not self._watchdog_task.done()
        return state

motor_service = MotorService()
