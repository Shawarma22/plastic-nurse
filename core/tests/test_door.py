import asyncio
import pytest
from fastapi.testclient import TestClient
from app.services.door_service import DoorService, DoorState
from app.hal.mock import MockDoorActuator

def test_door_status_authorized(client: TestClient, operator_token: str):
    response = client.get(
        "/api/v1/door/status",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "actuator" in data

def test_door_open_and_close_api(client: TestClient, operator_token: str):
    response = client.post(
        "/api/v1/door/open",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    assert response.json()["state"] == "opening"

    response = client.post(
        "/api/v1/door/stop",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_door_state_machine_cycle():
    mock_actuator = MockDoorActuator()
    service = DoorService(actuator=mock_actuator)
    assert service.state == DoorState.CLOSED

    await service.open_door()
    assert service.state == DoorState.OPENING

    await asyncio.sleep(0.05)
    await service.stop()
    assert service.state == DoorState.OPEN

    await service.close_door()
    assert service.state == DoorState.CLOSING

    await asyncio.sleep(0.05)
    await service.stop()
    assert service.state == DoorState.CLOSED
