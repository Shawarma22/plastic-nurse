import asyncio
import threading
import time
from typing import Optional, AsyncGenerator
from app.hal.base import BaseCameraDevice
from app.hal.factory import get_camera_device
from app.config import settings
from app.logger import logger

class CameraService:
    def __init__(self, device: Optional[BaseCameraDevice] = None) -> None:
        self.device: BaseCameraDevice = device or get_camera_device()
        self.latest_frame: bytes = b""
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.fps: int = settings.CAMERA_FPS

    def start(self) -> None:
        if self.is_running:
            return
        self.device.open()
        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Single-owner camera capture thread started")

    def stop(self) -> None:
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        self.device.close()
        logger.info("Camera service stopped")

    def _capture_loop(self) -> None:
        interval = 1.0 / max(1, self.fps)
        while self.is_running:
            start_time = time.time()
            success, frame = self.device.read_frame()
            if success and frame:
                with self._lock:
                    self.latest_frame = frame
            elapsed = time.time() - start_time
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_latest_frame(self) -> bytes:
        with self._lock:
            if self.latest_frame:
                return self.latest_frame
        success, frame = self.device.read_frame()
        if success and frame:
            with self._lock:
                self.latest_frame = frame
            return frame
        return b""

    async def generate_mjpeg_stream(self) -> AsyncGenerator[bytes, None]:
        interval = 1.0 / max(1, self.fps)
        while True:
            frame = self.get_latest_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(interval)

camera_service = CameraService()
