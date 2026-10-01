from typing import Dict, Any, Optional
from app.perception.intents import ParsedIntent, IntentType
from app.services.door_service import door_service, DoorService
from app.services.motor_service import motor_service, MotorService
from app.services.ws_manager import ws_manager, WebSocketManager
from app.logger import logger

class IntentDispatcher:
    def __init__(
        self,
        door_srv: Optional[DoorService] = None,
        motor_srv: Optional[MotorService] = None,
        ws_mgr: Optional[WebSocketManager] = None
    ) -> None:
        self.door_service = door_srv or door_service
        self.motor_service = motor_srv or motor_service
        self.ws_manager = ws_mgr or ws_manager

    async def dispatch(self, parsed: ParsedIntent) -> Dict[str, Any]:
        intent = parsed.intent
        result: Dict[str, Any] = {
            "intent": intent.value,
            "executed": False,
            "action": None,
            "details": {}
        }
        if intent == IntentType.OPEN_DOOR:
            details = await self.door_service.open_door()
            result.update({"executed": True, "action": "door_open", "details": details})
        elif intent == IntentType.CLOSE_DOOR:
            details = await self.door_service.close_door()
            result.update({"executed": True, "action": "door_close", "details": details})
        elif intent == IntentType.EMERGENCY_STOP:
            motor_res = await self.motor_service.stop()
            door_res = await self.door_service.stop()
            result.update({
                "executed": True,
                "action": "emergency_stop",
                "details": {"motors": motor_res, "door": door_res}
            })
            logger.warning("Emergency stop triggered via voice intent")
        elif intent == IntentType.MOVE_STOP:
            details = await self.motor_service.stop()
            result.update({"executed": True, "action": "motor_stop", "details": details})
        elif intent == IntentType.MOVE_FORWARD:
            details = await self.motor_service.forward(0.5)
            result.update({"executed": True, "action": "motor_forward", "details": details})
        elif intent == IntentType.MOVE_BACKWARD:
            details = await self.motor_service.backward(0.5)
            result.update({"executed": True, "action": "motor_backward", "details": details})
        elif intent == IntentType.CHECK_VITALS:
            result.update({
                "executed": True,
                "action": "check_vitals_prompt",
                "details": {"status": "prompt_initiated"}
            })
        elif intent == IntentType.CALL_NURSE:
            result.update({
                "executed": True,
                "action": "call_nurse_alert",
                "details": {"status": "alert_dispatched"}
            })
        else:
            result.update({"executed": False, "action": "none", "details": {"reason": "unknown_intent"}})

        await self.ws_manager.broadcast_state({
            "type": "intent_dispatched",
            "dispatch_result": result
        })
        return result

intent_dispatcher = IntentDispatcher()
