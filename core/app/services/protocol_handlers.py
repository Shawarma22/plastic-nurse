import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.config import settings
from app.schemas.protocol import StepDefinition, ProtocolState
from app.services.protocol_context import ProtocolExecutionContext
from app.services.tts_service import tts_service
from app.services.ble_bp_service import ble_bp_service
from app.services.door_service import door_service


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


class MeasureStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        target = step.target_vital or "general"
        measured_values: Dict[str, Any] = {}

        if target == "blood_pressure":
            if ble_bp_service.last_measurement:
                measured_values = {
                    "systolic": ble_bp_service.last_measurement.get("systolic", 120.0),
                    "diastolic": ble_bp_service.last_measurement.get("diastolic", 80.0),
                    "mean_arterial_pressure": ble_bp_service.last_measurement.get("mean_arterial_pressure", 93.3),
                    "pulse_rate": ble_bp_service.last_measurement.get("pulse_rate", 72.0),
                }
            elif settings.DROID_HAL == "mock":
                measured_values = {
                    "systolic": 122.0,
                    "diastolic": 80.0,
                    "mean_arterial_pressure": 94.0,
                    "pulse_rate": 72.0,
                }
            for k, v in measured_values.items():
                context.set_variable(f"blood_pressure_{k}", v)

        elif target == "pulse_oximeter":
            measured_values = {
                "spo2": 98.2,
                "heart_rate": 74.0,
                "confidence": 0.95,
            }
            for k, v in measured_values.items():
                context.set_variable(f"pulse_oximeter_{k}", v)

        elif target == "temperature":
            measured_values = {
                "ambient": 24.5,
                "object": 36.6,
            }
            for k, v in measured_values.items():
                context.set_variable(f"temperature_{k}", v)

        context.set_variable(f"{step.id}_measured", True)
        context.record_step(step.id, "measure", {"target_vital": target, "values": measured_values})
        return step.default_next


class BranchStepHandler(BaseStepHandler):
    def _evaluate(self, left: Any, operator: str, right: Any) -> bool:
        try:
            if operator == "==":
                return bool(left == right)
            if operator == "!=":
                return bool(left != right)
            if operator == ">":
                return float(left) > float(right)
            if operator == "<":
                return float(left) < float(right)
            if operator == ">=":
                return float(left) >= float(right)
            if operator == "<=":
                return float(left) <= float(right)
            if operator == "in":
                return left in right
        except (TypeError, ValueError):
            return False
        return False

    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        target_next = step.default_next
        matched_condition = None

        if step.conditions:
            for cond in step.conditions:
                var_val = context.get_variable(cond.variable)
                if var_val is not None and self._evaluate(var_val, cond.operator, cond.value):
                    target_next = cond.target_step
                    matched_condition = {
                        "variable": cond.variable,
                        "operator": cond.operator,
                        "value": cond.value,
                        "target_step": cond.target_step,
                    }
                    break

        context.record_step(
            step.id,
            "branch",
            {"matched_condition": matched_condition, "target_step": target_next},
        )
        return target_next


class DispenseStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        item_id = step.item_id or "unspecified"
        await door_service.open_door()
        await asyncio.sleep(0.3)
        await door_service.close_door()
        context.set_variable(f"dispensed_{item_id}", True)
        context.record_step(step.id, "dispense", {"item_id": item_id, "status": "completed"})
        return step.default_next


class FinishStepHandler(BaseStepHandler):
    async def execute(self, step: StepDefinition, context: ProtocolExecutionContext) -> Optional[str]:
        if step.text:
            tts_service.enqueue_speech(step.text)
        context.record_step(step.id, "finish", {"text": step.text})
        context.set_state(ProtocolState.COMPLETED)
        return None
