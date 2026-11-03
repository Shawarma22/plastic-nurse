import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.schemas.protocol import ProtocolSchema, StepDefinition, StepType, ProtocolMetadata
from app.services.protocol_parser import protocol_parser, ProtocolValidationError
from app.services.protocol_context import ProtocolExecutionContext
from app.services.protocol_engine import protocol_engine


@pytest.fixture(autouse=True)
def setup_protocols():
    proto_dir = Path(__file__).resolve().parent.parent / "protocols"
    protocol_engine.load_protocols(proto_dir)


def test_protocol_schema_and_parser():
    valid_yaml = """
metadata:
  id: test_proto
  name: Test Protocol
  version: 1.0.0
initial_step: step_1
steps:
  - id: step_1
    type: prompt
    text: Hello
    default_next: step_2
  - id: step_2
    type: finish
    text: Done
"""
    schema = protocol_parser.parse_string(valid_yaml)
    assert schema.metadata.id == "test_proto"
    assert len(schema.steps) == 2

    invalid_yaml = """
metadata:
  id: bad_proto
  name: Bad Protocol
initial_step: missing_step
steps:
  - id: step_1
    type: prompt
"""
    with pytest.raises(ProtocolValidationError):
        protocol_parser.parse_string(invalid_yaml)


def test_protocol_parser_duplicate_step():
    meta = ProtocolMetadata(id="dup", name="Dup")
    s1 = StepDefinition(id="step_1", type=StepType.PROMPT, text="a")
    s2 = StepDefinition(id="step_1", type=StepType.FINISH, text="b")
    schema = ProtocolSchema(metadata=meta, initial_step="step_1", steps=[s1, s2])
    errors = protocol_parser.validate(schema)
    assert len(errors) > 0


def test_protocol_execution_context():
    ctx = ProtocolExecutionContext(protocol_id="test_proto", session_uid="sess-100")
    assert ctx.protocol_id == "test_proto"
    assert ctx.session_uid == "sess-100"
    ctx.set_variable("patient_observed", True)
    assert ctx.get_variable("patient_observed") is True
    ctx.record_step("step_1", "prompt", {"text": "hello"})
    snap = ctx.snapshot()
    assert snap["step_count"] == 1
    assert snap["variables"]["patient_observed"] is True


@pytest.mark.asyncio
async def test_protocol_engine_checkin_flow():
    ctx = await protocol_engine.start_protocol("checkin", session_uid="checkin-test-01")
    assert ctx.protocol_id == "checkin"
    await asyncio.sleep(3.2)
    status = protocol_engine.get_status()
    assert status["state"] in ("running", "completed")


@pytest.mark.asyncio
async def test_protocol_engine_branching_flow():
    ctx = await protocol_engine.start_protocol(
        "vitals_routine",
        session_uid="branch-test-01",
        initial_vars={"requires_dispense": False},
    )
    assert ctx.protocol_id == "vitals_routine"
    await asyncio.sleep(0.5)
    status = protocol_engine.get_status()
    assert status["has_active_execution"] is True


@pytest.mark.asyncio
async def test_protocol_engine_pause_resume_abort():
    ctx = await protocol_engine.start_protocol("checkin", session_uid="pause-test-01")
    assert ctx.protocol_id == "checkin"
    paused = await protocol_engine.pause_protocol()
    assert paused is True
    assert protocol_engine.get_status()["state"] == "paused"

    resumed = await protocol_engine.resume_protocol()
    assert resumed is True
    assert protocol_engine.get_status()["state"] == "running"

    aborted = await protocol_engine.abort_protocol("Test abort")
    assert aborted is True
    assert protocol_engine.get_status()["state"] == "aborted"


def test_protocol_rest_api(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}

    res_list = client.get("/api/v1/protocols", headers=headers)
    assert res_list.status_code == 200
    protocols = res_list.json()
    assert len(protocols) >= 2
    proto_ids = [p["id"] for p in protocols]
    assert "checkin" in proto_ids

    res_detail = client.get("/api/v1/protocols/checkin", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["metadata"]["id"] == "checkin"

    res_status = client.get("/api/v1/protocols/status", headers=headers)
    assert res_status.status_code == 200
    assert "loaded_protocols_count" in res_status.json()

    res_start = client.post(
        "/api/v1/protocols/start",
        json={"protocol_id": "checkin", "session_uid": "api-sess-01"},
        headers=headers,
    )
    assert res_start.status_code == 200
    start_data = res_start.json()
    assert start_data["protocol_id"] == "checkin"

    res_pause = client.post("/api/v1/protocols/pause", headers=headers)
    assert res_pause.status_code == 200

    res_resume = client.post("/api/v1/protocols/resume", headers=headers)
    assert res_resume.status_code == 200

    res_abort = client.post("/api/v1/protocols/abort", json={"reason": "api test stop"}, headers=headers)
    assert res_abort.status_code == 200
    assert res_abort.json()["success"] is True
