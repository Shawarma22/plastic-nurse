import pytest
from app.hal.mock import MockMotorController, MockDoorActuator, MockCameraDevice

@pytest.mark.asyncio
async def test_mock_motor_controller():
    motor = MockMotorController()
    assert motor.left_speed == 0.0
    assert motor.right_speed == 0.0

    await motor.forward(0.8)
    assert motor.left_speed == 0.8
    assert motor.right_speed == 0.8
    assert motor.get_state()["is_moving"] is True

    await motor.turn_left(0.5)
    assert motor.left_speed == -0.5
    assert motor.right_speed == 0.5

    await motor.stop()
    assert motor.left_speed == 0.0
    assert motor.right_speed == 0.0
    assert motor.get_state()["is_moving"] is False

@pytest.mark.asyncio
async def test_mock_door_actuator():
    door = MockDoorActuator()
    assert door.position == 0.0
    assert await door.is_close_limit_reached() is True
    assert await door.is_open_limit_reached() is False

    await door.start_open()
    assert door.is_moving_open is True
    assert door.is_moving_close is False

    await door.stop()
    assert door.is_moving_open is False

def test_mock_camera_device():
    camera = MockCameraDevice(width=320, height=240)
    assert camera.is_opened is False

    success = camera.open()
    assert success is True
    assert camera.is_opened is True

    ret, frame_bytes = camera.read_frame()
    assert ret is True
    assert len(frame_bytes) > 0
    assert frame_bytes.startswith(b"\xff\xd8")

    camera.close()
    assert camera.is_opened is False
