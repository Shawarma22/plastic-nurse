import asyncio
import pytest
from fastapi.testclient import TestClient
from app.services.motor_service import MotorService
from app.hal.mock import MockMotorController

def test_motor_unauthorized(client: TestClient):
    response = client.post("/api/v1/motors/forward", json={"speed": 0.5})
    assert response.status_code == 401

def test_motor_forward_authorized(client: TestClient, operator_token: str):
    response = client.post(
        "/api/v1/motors/forward",
        json={"speed": 0.75},
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left_speed"] == 0.75
    assert data["right_speed"] == 0.75

def test_motor_command_turn(client: TestClient, operator_token: str):
    response = client.post(
        "/api/v1/motors/command",
        json={"left_speed": -0.5, "right_speed": 0.5},
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left_speed"] == -0.5
    assert data["right_speed"] == 0.5

def test_motor_stop(client: TestClient, operator_token: str):
    response = client.post(
        "/api/v1/motors/stop",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["left_speed"] == 0.0
    assert data["right_speed"] == 0.0

@pytest.mark.asyncio
async def test_motor_watchdog_auto_stop():
    mock_hal = MockMotorController()
    service = MotorService(controller=mock_hal, timeout_sec=0.05)

    await service.forward(1.0)
    assert mock_hal.left_speed == 1.0
    assert mock_hal.right_speed == 1.0

    await asyncio.sleep(0.08)
    assert mock_hal.left_speed == 0.0
    assert mock_hal.right_speed == 0.0
