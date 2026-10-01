import pytest
from fastapi.testclient import TestClient
from app.perception.intents import (
    RuleBasedIntentParser,
    IntentType,
    ParsedIntent
)
from app.perception.intent_dispatcher import IntentDispatcher

def test_intent_parser_rules():
    parser = RuleBasedIntentParser()

    p_open = parser.parse("Please open the door for me!")
    assert p_open.intent == IntentType.OPEN_DOOR
    assert p_open.confidence >= 0.90

    p_close = parser.parse("Can you close the door now?")
    assert p_close.intent == IntentType.CLOSE_DOOR
    assert p_close.confidence >= 0.90

    p_estop = parser.parse("EMERGENCY STOP IMMEDIATELY")
    assert p_estop.intent == IntentType.EMERGENCY_STOP
    assert p_estop.confidence == 1.0

    p_vitals = parser.parse("time to measure my vitals")
    assert p_vitals.intent == IntentType.CHECK_VITALS
    assert p_vitals.confidence >= 0.90

    p_nurse = parser.parse("call the nurse I need help")
    assert p_nurse.intent == IntentType.CALL_NURSE
    assert p_nurse.confidence >= 0.90

    p_fwd = parser.parse("move forward slowly")
    assert p_fwd.intent == IntentType.MOVE_FORWARD

    p_bwd = parser.parse("go backward")
    assert p_bwd.intent == IntentType.MOVE_BACKWARD

    p_stop = parser.parse("stop moving")
    assert p_stop.intent == IntentType.MOVE_STOP

    p_unknown = parser.parse("what is the weather today")
    assert p_unknown.intent == IntentType.UNKNOWN
    assert p_unknown.confidence == 0.0

def test_intent_parser_edge_cases():
    parser = RuleBasedIntentParser()
    assert parser.parse("").intent == IntentType.UNKNOWN
    assert parser.parse("   ").intent == IntentType.UNKNOWN
    assert parser.parse("...???!!!").intent == IntentType.UNKNOWN

    res = parser.parse("OPEN   DOOR!!!")
    assert res.intent == IntentType.OPEN_DOOR

@pytest.mark.asyncio
async def test_intent_dispatcher():
    dispatcher = IntentDispatcher()

    parsed_open = ParsedIntent(intent=IntentType.OPEN_DOOR, confidence=0.95, raw_text="open door")
    res_open = await dispatcher.dispatch(parsed_open)
    assert res_open["executed"] is True
    assert res_open["action"] == "door_open"

    parsed_close = ParsedIntent(intent=IntentType.CLOSE_DOOR, confidence=0.95, raw_text="close door")
    res_close = await dispatcher.dispatch(parsed_close)
    assert res_close["executed"] is True
    assert res_close["action"] == "door_close"

    parsed_estop = ParsedIntent(intent=IntentType.EMERGENCY_STOP, confidence=1.0, raw_text="estop")
    res_estop = await dispatcher.dispatch(parsed_estop)
    assert res_estop["executed"] is True
    assert res_estop["action"] == "emergency_stop"

    parsed_unknown = ParsedIntent(intent=IntentType.UNKNOWN, confidence=0.0, raw_text="gibberish")
    res_unknown = await dispatcher.dispatch(parsed_unknown)
    assert res_unknown["executed"] is False

def test_intent_api_endpoint(client: TestClient, operator_token: str):
    res_unauth = client.post("/api/v1/perception/intent/parse", json={"text": "open door"})
    assert res_unauth.status_code == 401

    headers = {"Authorization": f"Bearer {operator_token}"}
    res_parse = client.post(
        "/api/v1/perception/intent/parse",
        json={"text": "please open the door", "auto_dispatch": False},
        headers=headers
    )
    assert res_parse.status_code == 200
    data = res_parse.json()
    assert data["parsed"]["intent"] == "open_door"
    assert data["dispatched"] is False

    res_dispatch = client.post(
        "/api/v1/perception/intent/parse",
        json={"text": "stop moving", "auto_dispatch": True},
        headers=headers
    )
    assert res_dispatch.status_code == 200
    data_disp = res_dispatch.json()
    assert data_disp["parsed"]["intent"] == "move_stop"
    assert data_disp["dispatched"] is True
    assert data_disp["dispatch_result"]["action"] == "motor_stop"
