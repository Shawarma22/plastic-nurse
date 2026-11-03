import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from app.schemas.protocol import ProtocolSchema, ProtocolState, StepType
from app.services.protocol_parser import protocol_parser
from app.services.protocol_context import ProtocolExecutionContext
from app.services.protocol_handlers import (
    BaseStepHandler,
    PromptStepHandler,
    WaitStepHandler,
    MeasureStepHandler,
    BranchStepHandler,
    DispenseStepHandler,
    FinishStepHandler,
)
from app.services.ws_manager import ws_manager

logger = logging.getLogger("droid.protocol")


class ProtocolEngine:
    def __init__(self) -> None:
        self.protocols: Dict[str, ProtocolSchema] = {}
        self.active_context: Optional[ProtocolExecutionContext] = None
        self._task: Optional[asyncio.Task] = None
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._handlers: Dict[StepType, BaseStepHandler] = {
            StepType.PROMPT: PromptStepHandler(),
            StepType.WAIT: WaitStepHandler(),
            StepType.MEASURE: MeasureStepHandler(),
            StepType.BRANCH: BranchStepHandler(),
            StepType.DISPENSE: DispenseStepHandler(),
            StepType.FINISH: FinishStepHandler(),
        }

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def _broadcast_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        msg = {
            "type": "protocol_event",
            "event": event_name,
            "protocol_id": self.active_context.protocol_id if self.active_context else None,
            "execution_id": self.active_context.execution_id if self.active_context else None,
            "payload": payload,
        }
        try:
            await ws_manager.broadcast_state(msg)
        except Exception:
            pass

    def load_protocols(self, dir_path: Union[str, Path] = "protocols") -> int:
        loaded = protocol_parser.load_directory(dir_path)
        self.protocols.update(loaded)
        return len(loaded)

    def get_protocol(self, protocol_id: str) -> Optional[ProtocolSchema]:
        return self.protocols.get(protocol_id)

    def list_protocols(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.metadata.id,
                "name": p.metadata.name,
                "version": p.metadata.version,
                "description": p.metadata.description,
                "estimated_duration_sec": p.metadata.estimated_duration_sec,
                "step_count": len(p.steps),
            }
            for p in self.protocols.values()
        ]

    async def start_protocol(
        self,
        protocol_id: str,
        session_uid: Optional[str] = None,
        initial_vars: Optional[Dict[str, Any]] = None,
    ) -> ProtocolExecutionContext:
        if protocol_id not in self.protocols:
            raise ValueError(f"Protocol '{protocol_id}' is not loaded")

        if self.active_context and self.active_context.state in (ProtocolState.RUNNING, ProtocolState.PAUSED):
            raise RuntimeError("Another protocol execution is currently active")

        schema = self.protocols[protocol_id]
        context = ProtocolExecutionContext(
            protocol_id=protocol_id,
            session_uid=session_uid,
            initial_variables=initial_vars,
        )
        self.active_context = context
        self._pause_event.set()
        context.set_state(ProtocolState.RUNNING)
        await self._broadcast_event("protocol_started", {"protocol_id": protocol_id, "session_uid": context.session_uid})
        self._task = asyncio.create_task(self._run_execution(context, schema))
        return context

    async def pause_protocol(self) -> bool:
        if not self.active_context or self.active_context.state != ProtocolState.RUNNING:
            return False
        self._pause_event.clear()
        self.active_context.set_state(ProtocolState.PAUSED)
        await self._broadcast_event("protocol_paused", {"current_step_id": self.active_context.current_step_id})
        return True

    async def resume_protocol(self) -> bool:
        if not self.active_context or self.active_context.state != ProtocolState.PAUSED:
            return False
        self.active_context.set_state(ProtocolState.RUNNING)
        self._pause_event.set()
        await self._broadcast_event("protocol_resumed", {"current_step_id": self.active_context.current_step_id})
        return True

    async def abort_protocol(self, reason: Optional[str] = None) -> bool:
        if not self.active_context or self.active_context.state not in (ProtocolState.RUNNING, ProtocolState.PAUSED):
            return False
        self._pause_event.set()
        self.active_context.error_message = reason or "Aborted by user request"
        self.active_context.set_state(ProtocolState.ABORTED)
        await self._broadcast_event("protocol_aborted", {"reason": self.active_context.error_message})
        if self._task and not self._task.done():
            self._task.cancel()
        return True

    def get_status(self) -> Dict[str, Any]:
        if not self.active_context:
            return {
                "state": ProtocolState.IDLE.value,
                "has_active_execution": False,
                "loaded_protocols_count": len(self.protocols),
            }
        snap = self.active_context.snapshot()
        snap["has_active_execution"] = True
        snap["loaded_protocols_count"] = len(self.protocols)
        return snap

    async def _run_execution(self, context: ProtocolExecutionContext, schema: ProtocolSchema) -> None:
        step_map = {s.id: s for s in schema.steps}
        next_step_id: Optional[str] = schema.initial_step

        try:
            while next_step_id:
                if context.state != ProtocolState.RUNNING:
                    if context.state == ProtocolState.PAUSED:
                        await self._pause_event.wait()
                    else:
                        break

                context.current_step_id = next_step_id
                step = step_map.get(next_step_id)
                if not step:
                    context.error_message = f"Step '{next_step_id}' not found"
                    context.set_state(ProtocolState.ERROR)
                    await self._broadcast_event("protocol_error", {"error": context.error_message})
                    break

                await self._broadcast_event("step_entered", {"step_id": step.id, "step_type": step.type.value})
                handler = self._handlers.get(step.type)
                if not handler:
                    context.error_message = f"Handler for step type '{step.type}' not found"
                    context.set_state(ProtocolState.ERROR)
                    await self._broadcast_event("protocol_error", {"error": context.error_message})
                    break

                next_step_id = await handler.execute(step, context)
                await self._broadcast_event("step_exited", {"step_id": step.id, "next_step_id": next_step_id})

            if context.state == ProtocolState.RUNNING:
                context.current_step_id = None
                context.set_state(ProtocolState.COMPLETED)
                await self._broadcast_event("protocol_completed", {"session_uid": context.session_uid})

        except asyncio.CancelledError:
            context.set_state(ProtocolState.ABORTED)
            await self._broadcast_event("protocol_aborted", {"reason": "Cancelled task"})
        except Exception as e:
            logger.error(f"Error executing protocol '{schema.metadata.id}': {e}")
            context.error_message = str(e)
            context.set_state(ProtocolState.ERROR)
            await self._broadcast_event("protocol_error", {"error": str(e)})


protocol_engine = ProtocolEngine()
