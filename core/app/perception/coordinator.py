import asyncio
from typing import Dict, Any, Optional, List, Callable
from app.perception.wake_state import PerceptionLifecycleState, LifecycleTransitionEvent
from app.perception.wake_base import BaseWakeWordDetector
from app.perception.keyword_spotter import KeywordSpotter
from app.services.ws_manager import ws_manager, WebSocketManager
from app.logger import logger

class PerceptionCoordinator:
    def __init__(
        self,
        wake_detector: Optional[BaseWakeWordDetector] = None,
        ws_mgr: Optional[WebSocketManager] = None
    ) -> None:
        self.state = PerceptionLifecycleState.IDLE
        self.wake_detector = wake_detector or KeywordSpotter()
        self.ws_manager = ws_mgr or ws_manager
        self.history: List[LifecycleTransitionEvent] = []
        self._listeners: List[Callable[[LifecycleTransitionEvent], None]] = []
        self._command_audio_buffer = bytearray()
        self._lock = asyncio.Lock()

    def add_listener(self, callback: Callable[[LifecycleTransitionEvent], None]) -> None:
        self._listeners.append(callback)

    def get_state(self) -> PerceptionLifecycleState:
        return self.state

    def get_command_audio(self) -> bytes:
        return bytes(self._command_audio_buffer)

    def clear_command_audio(self) -> None:
        self._command_audio_buffer.clear()

    async def feed_audio_chunk(self, chunk: bytes) -> Optional[LifecycleTransitionEvent]:
        if not chunk:
            return None

        if self.state == PerceptionLifecycleState.IDLE:
            res = self.wake_detector.process_audio_chunk(chunk)
            if res.detected:
                self.clear_command_audio()
                event = await self.transition_to(
                    PerceptionLifecycleState.WAKE_DETECTED,
                    trigger="wake_word_detected",
                    metadata={"wake_word": res.wake_word, "confidence": res.confidence}
                )
                await self.transition_to(
                    PerceptionLifecycleState.LISTENING,
                    trigger="auto_listen_start"
                )
                return event
        elif self.state == PerceptionLifecycleState.LISTENING:
            self._command_audio_buffer.extend(chunk)

        return None

    async def transition_to(
        self,
        new_state: PerceptionLifecycleState,
        trigger: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LifecycleTransitionEvent:
        async with self._lock:
            event = LifecycleTransitionEvent(
                previous_state=self.state,
                new_state=new_state,
                trigger=trigger,
                metadata=metadata or {}
            )
            self.state = new_state
            self.history.append(event)
            if len(self.history) > 100:
                self.history.pop(0)

            logger.info(f"Perception state changed: {event.previous_state} -> {event.new_state} (trigger: {trigger})")

            for cb in self._listeners:
                try:
                    cb(event)
                except Exception as e:
                    logger.error(f"Error in perception transition listener: {e}")

            await self.ws_manager.broadcast_state({
                "type": "perception_lifecycle",
                "lifecycle_event": event.to_dict()
            })
            return event

    async def reset(self) -> None:
        async with self._lock:
            self.state = PerceptionLifecycleState.IDLE
            self.wake_detector.reset()
            self.clear_command_audio()
            logger.info("Perception coordinator reset to IDLE")

coordinator = PerceptionCoordinator()
