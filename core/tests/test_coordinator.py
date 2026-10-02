import pytest
from fastapi.testclient import TestClient
from app.perception.wake_state import PerceptionLifecycleState
from app.perception.wake_mock import MockWakeWordDetector
from app.perception.coordinator import PerceptionCoordinator

@pytest.mark.asyncio
async def test_coordinator_lifecycle():
    mock_wake = MockWakeWordDetector(wake_word="hey droid", auto_trigger_after_chunks=1)
    coord = PerceptionCoordinator(wake_detector=mock_wake)
    assert coord.get_state() == PerceptionLifecycleState.IDLE

    event = await coord.feed_audio_chunk(b"trigger_chunk")
    assert event is not None
    assert event.previous_state == PerceptionLifecycleState.IDLE
    assert event.new_state == PerceptionLifecycleState.WAKE_DETECTED
    assert coord.get_state() == PerceptionLifecycleState.LISTENING

    await coord.feed_audio_chunk(b"speech_data_1")
    await coord.feed_audio_chunk(b"speech_data_2")
    assert coord.get_command_audio() == b"speech_data_1speech_data_2"

    result = await coord.finish_listening_and_dispatch(override_text="open the door")
    assert result["transcript"] == "open the door"
    assert result["parsed"]["intent"] == "open_door"
    assert result["dispatch_result"]["executed"] is True
    assert coord.get_state() == PerceptionLifecycleState.IDLE
    assert coord.get_command_audio() == b""

@pytest.mark.asyncio
async def test_coordinator_reset():
    coord = PerceptionCoordinator()
    await coord.transition_to(PerceptionLifecycleState.LISTENING, trigger="test")
    assert coord.get_state() == PerceptionLifecycleState.LISTENING

    await coord.reset()
    assert coord.get_state() == PerceptionLifecycleState.IDLE
    assert len(coord.get_command_audio()) == 0

def test_coordinator_api_endpoints(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}

    res_status = client.get("/api/v1/perception/coordinator/status", headers=headers)
    assert res_status.status_code == 200
    data = res_status.json()
    assert "state" in data
    assert "history" in data

    res_wake = client.post("/api/v1/perception/coordinator/trigger-wake", headers=headers)
    assert res_wake.status_code == 200
    wake_data = res_wake.json()
    assert wake_data["status"] == "triggered"
    assert wake_data["state"] == "listening"

    res_exec = client.post(
        "/api/v1/perception/coordinator/execute-command",
        json={"text": "close the door"},
        headers=headers
    )
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["parsed"]["intent"] == "close_door"
    assert exec_data["dispatch_result"]["executed"] is True

    res_reset = client.post("/api/v1/perception/coordinator/reset", headers=headers)
    assert res_reset.status_code == 200
    reset_data = res_reset.json()
    assert reset_data["status"] == "reset"
    assert reset_data["state"] == "idle"
