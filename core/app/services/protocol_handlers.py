import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.protocol import StepDefinition, ProtocolState
from app.services.protocol_context import ProtocolExecutionContext
from app.services.tts_service import tts_service


class BaseStepHandler(ABC):
    @abstractmethod
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        pass


class PromptStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        if step.text:
            tts_service.enqueue_speech(step.text)
            context.set_variable(f"prompt_{step.id}_spoken", True)
        context.record_step(step.id, "prompt", {"text": step.text})
        return step.default_next


class WaitStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        duration = step.duration_sec if step.duration_sec is not None else 1.0
        await asyncio.sleep(duration)
        context.set_variable(f"wait_{step.id}_completed", True)
        context.record_step(step.id, "wait", {"duration_sec": duration})
        return step.default_next


class FinishStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        if step.text:
            tts_service.enqueue_speech(step.text)
        context.record_step(step.id, "finish", {"text": step.text})
        context.set_state(ProtocolState.COMPLETED)
        return None
