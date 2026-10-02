import asyncio
from typing import Dict, Any, Optional, List, Callable
from app.perception.wake_state import PerceptionLifecycleState, LifecycleTransitionEvent
from app.perception.wake_base import BaseWakeWordDetector
from app.perception.keyword_spotter import KeywordSpotter
from app.perception.stt import VoskSpeechRecognizer, BaseSpeechRecognizer
from app.perception.intents import intent_parser, RuleBasedIntentParser
from app.perception.intent_dispatcher import intent_dispatcher, IntentDispatcher
from app.services.ws_manager import ws_manager, WebSocketManager
from app.logger import logger

class PerceptionCoordinator:
    def __init__(
        self,
        wake_detector: Optional[BaseWakeWordDetector] = None,
        stt: Optional[BaseSpeechRecognizer] = None,
        parser: Optional[RuleBasedIntentParser] = None,
        dispatcher: Optional[IntentDispatcher] = None,
        ws_mgr: Optional[WebSocketManager] = None
    ) -> None:
        self.state = PerceptionLifecycleState.IDLE
        self.wake_detector = wake_detector or KeywordSpotter()
        self.stt = stt or VoskSpeechRecognizer()
        self.intent_parser = parser or intent_parser
        self.intent_dispatcher = dispatcher or intent_dispatcher
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

    async def finish_listening_and_dispatch(
        self,
        override_text: Optional[str] = None
    ) -> Dict[str, Any]:
        await self.transition_to(
            PerceptionLifecycleState.PARSING_INTENT,
            trigger="speech_end"
        )
        if override_text:
            transcript = override_text
        else:
            audio = self.get_command_audio()
            res = self.stt.accept_waveform(audio) if audio else None
            if not res or not res.transcript:
                res = self.stt.get_final_result()
            transcript = res.transcript if res else ""

        parsed = self.intent_parser.parse(transcript)
        await self.transition_to(
            PerceptionLifecycleState.EXECUTING_ACTION,
            trigger="intent_parsed",
            metadata={"intent": parsed.intent.value, "transcript": transcript}
        )

        dispatch_res = await self.intent_dispatcher.dispatch(parsed)

        await self.transition_to(
            PerceptionLifecycleState.COOLDOWN,
            trigger="action_completed"
        )
        await self.transition_to(
            PerceptionLifecycleState.IDLE,
            trigger="cooldown_finished"
        )
        self.clear_command_audio()

        return {
            "transcript": transcript,
            "parsed": parsed.to_dict(),
            "dispatch_result": dispatch_res
        }

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
