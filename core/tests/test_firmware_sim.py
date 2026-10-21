import json
import struct
from collections import deque
from pathlib import Path
from app.hal.firmware_sim import (
    FirmwareSimulator,
    MockMqttClient,
    TOPIC_STATUS,
    TOPIC_VITALS_PROCESSED,
    TOPIC_VITALS_RAW,
    TOPIC_VITALS_EVENTS,
    TOPIC_CMD_DISPENSE,
)


def test_packet_structure():
    sim = FirmwareSimulator()
    packet = sim.generate_packet()

    assert "seq" in packet
    assert "ts" in packet
    assert "ppg" in packet
    assert "ecg" in packet
    assert "bat" in packet
    assert "status" in packet

    ppg = packet["ppg"]
    assert ppg["ir"] > 0
    assert ppg["red"] > 0
    assert 50.0 <= ppg["bpm"] <= 120.0
    assert 90.0 <= ppg["spo2"] <= 100.0
    assert 0.0 <= ppg["conf"] <= 1.0
    assert ppg["finger"] is True

    ecg = packet["ecg"]
    assert 0 <= ecg["raw"] <= 4095
    assert ecg["lead_off"] is False

    assert packet["bat"] >= 3300
    assert packet["status"] == (0x01 | 0x02 | 0x04)


def test_packet_serialization():
    sim = FirmwareSimulator()
    packet = sim.generate_packet()
    serialized = sim.serialize_packet(packet)

    assert isinstance(serialized, str)
    decoded = json.loads(serialized)
    assert decoded["seq"] == packet["seq"]
    assert decoded["ppg"]["bpm"] == packet["ppg"]["bpm"]
    assert decoded["ecg"]["raw"] == packet["ecg"]["raw"]


def test_disconnect_ppg():
    sim = FirmwareSimulator(disconnect_ppg=True)
    packet = sim.generate_packet()

    assert packet["ppg"]["finger"] is False
    assert packet["ppg"]["bpm"] == 0.0
    assert packet["ppg"]["spo2"] == 0.0
    assert packet["ppg"]["conf"] == 0.0
    assert (packet["status"] & 0x01) == 0


def test_disconnect_ecg():
    sim = FirmwareSimulator(disconnect_ecg=True)
    packet = sim.generate_packet()

    assert packet["ecg"]["lead_off"] is True
    assert packet["ecg"]["raw"] == 0
    assert (packet["status"] & 0x08) == 0x08


def test_drop_rate():
    sim = FirmwareSimulator(drop_rate=1.0)
    packets = list(sim.stream_packets(count=20, interval_s=0.0))
    assert len(packets) == 0


def test_streaming_packets():
    sim = FirmwareSimulator(drop_rate=0.0)
    packets = list(sim.stream_packets(count=5, interval_s=0.0))
    assert len(packets) == 5

    seqs = []
    for line in packets:
        data = json.loads(line)
        seqs.append(data["seq"])
    assert seqs == [1, 2, 3, 4, 5]


def test_firmware_sim_json_contract():
    sim = FirmwareSimulator()
    packet = sim.generate_packet()
    serialized = sim.serialize_packet(packet)
    decoded = json.loads(serialized)

    expected_keys = {"seq", "ts", "ppg", "ecg", "bat", "status"}
    assert set(decoded.keys()) == expected_keys

    expected_ppg_keys = {"ir", "red", "bpm", "spo2", "conf", "finger"}
    assert set(decoded["ppg"].keys()) == expected_ppg_keys

    expected_ecg_keys = {"raw", "lead_off"}
    assert set(decoded["ecg"].keys()) == expected_ecg_keys


def test_synthetic_ppg_dsp_processing():
    sim = FirmwareSimulator()
    packets = [sim.generate_packet() for _ in range(50)]

    for p in packets:
        ppg = p["ppg"]
        assert ppg["finger"] is True
        assert ppg["ir"] >= 200000
        assert ppg["red"] >= 200000
        assert 60.0 <= ppg["bpm"] <= 90.0
        assert 95.0 <= ppg["spo2"] <= 100.0
        assert ppg["conf"] >= 0.90


def test_firmware_file_integrity():
    repo_root = Path(__file__).resolve().parents[2]
    firmware_dir = repo_root / "firmware"
    assert firmware_dir.exists()

    required_headers = [
        "pinout.h",
        "config.h",
        "tasks.h",
        "i2c_bus.h",
        "status_led.h",
        "sensor_types.h",
        "packet_serializer.h",
        "max30102_regs.h",
        "max30102.h",
        "dsp_filters.h",
        "ad8232.h",
        "ecg_filters.h",
        "mlx90614_regs.h",
        "mlx90614.h",
        "temp_filters.h",
        "stepper.h",
        "mqtt_topics.h",
        "network_manager.h",
        "mqtt_publisher.h",
        "telemetry_ring_buffer.h",
    ]
    for header in required_headers:
        path = firmware_dir / "include" / header
        assert path.exists()

    required_src = [
        "main.cpp",
        "i2c_bus.cpp",
        "status_led.cpp",
        "heartbeat_task.cpp",
        "packet_serializer.cpp",
        "max30102.cpp",
        "dsp_filters.cpp",
        "ppg_task.cpp",
        "ad8232.cpp",
        "ecg_task.cpp",
        "mlx90614.cpp",
        "stepper.cpp",
        "temp_task.cpp",
        "dispense_task.cpp",
        "network_manager.cpp",
        "mqtt_publisher.cpp",
        "telemetry_task.cpp",
    ]
    for src in required_src:
        path = firmware_dir / "src" / src
        assert path.exists()


def test_synthetic_ecg_waveform_generation():
    sim = FirmwareSimulator()
    samples = [sim.generate_ecg_sample(t * 0.004) for t in range(500)]
    assert len(samples) == 500
    assert all(0 <= s <= 4095 for s in samples)

    max_val = max(samples)
    min_val = min(samples)
    assert max_val >= 3200
    assert min_val <= 1900
    assert any(s > 3000 for s in samples)


def test_firmware_sim_temperature_telemetry():
    sim = FirmwareSimulator(include_temp=True)
    packet = sim.generate_packet()

    assert "temp" in packet
    temp = packet["temp"]
    assert "amb" in temp
    assert "obj" in temp
    assert "conf" in temp
    assert "target" in temp

    assert 20.0 <= temp["amb"] <= 30.0
    assert 35.0 <= temp["obj"] <= 38.0
    assert 0.90 <= temp["conf"] <= 1.0
    assert temp["target"] is True
    assert (packet["status"] & 0x20) == 0x20
    assert (packet["status"] & 0x40) == 0x40


def test_firmware_sim_temperature_disconnect_and_no_target():
    sim_disc = FirmwareSimulator(include_temp=True, disconnect_temp=True)
    p_disc = sim_disc.generate_packet()
    assert p_disc["temp"]["amb"] == 0.0
    assert p_disc["temp"]["obj"] == 0.0
    assert p_disc["temp"]["conf"] == 0.0
    assert p_disc["temp"]["target"] is False

    sim_notarget = FirmwareSimulator(include_temp=True, target_temp_present=False)
    p_notarget = sim_notarget.generate_packet()
    assert p_notarget["temp"]["target"] is False
    assert p_notarget["temp"]["conf"] < 0.20
    assert (p_notarget["status"] & 0x40) == 0
    assert (p_notarget["status"] & 0x20) == 0x20


def test_firmware_sim_dispenser_telemetry_and_actions():
    sim = FirmwareSimulator(include_dispenser=True)
    packet = sim.generate_packet()

    assert "dispenser" in packet
    disp = packet["dispenser"]
    assert disp["comp"] == 0
    assert disp["target"] == 0
    assert disp["moving"] is False
    assert disp["homed"] is True
    assert disp["stall"] is False

    assert sim.move_to_compartment(5) is True
    assert sim.current_compartment == 5
    assert sim.target_compartment == 5

    assert sim.move_to_compartment(14) is False
    assert sim.move_to_compartment(-1) is False

    sim.trigger_stall()
    p_stall = sim.generate_packet()
    assert p_stall["dispenser"]["stall"] is True

    sim.clear_stall()
    p_clear = sim.generate_packet()
    assert p_clear["dispenser"]["stall"] is False

    sim.home_dispenser()
    assert sim.current_compartment == 0
    assert sim.dispenser_homed is True


def test_firmware_sim_combined_telemetry_packet():
    sim = FirmwareSimulator(include_temp=True, include_dispenser=True)
    packet = sim.generate_packet()
    serialized = sim.serialize_packet(packet)
    decoded = json.loads(serialized)

    expected_keys = {"seq", "ts", "ppg", "ecg", "temp", "dispenser", "bat", "status"}
    assert set(decoded.keys()) == expected_keys
    assert set(decoded["temp"].keys()) == {"amb", "obj", "conf", "target"}
    assert set(decoded["dispenser"].keys()) == {"comp", "target", "moving", "homed", "stall"}


def test_stepper_carousel_math_shortest_path():
    total_rev_steps = 200 * 16
    total_comps = 14

    def comp_to_steps(idx: int) -> int:
        return (idx * total_rev_steps) // total_comps

    def shortest_delta(from_c: int, to_c: int) -> int:
        delta = comp_to_steps(to_c) - comp_to_steps(from_c)
        if delta > total_rev_steps // 2:
            delta -= total_rev_steps
        elif delta < -total_rev_steps // 2:
            delta += total_rev_steps
        return delta

    assert shortest_delta(0, 13) < 0
    assert shortest_delta(13, 0) > 0
    assert abs(shortest_delta(0, 13)) == abs(shortest_delta(13, 0))
    assert shortest_delta(0, 7) == total_rev_steps // 2
    assert shortest_delta(3, 3) == 0


def test_temperature_plausibility_and_confidence_logic():
    min_c = 30.0
    max_c = 43.0

    def is_plausible(temp: float) -> bool:
        return min_c <= temp <= max_c

    assert is_plausible(36.6) is True
    assert is_plausible(37.2) is True
    assert is_plausible(25.0) is False
    assert is_plausible(45.0) is False

    def calc_confidence(amb: float, obj: float) -> float:
        if obj < 25.0 or obj > 45.0:
            return 0.0
        delta = obj - amb
        if delta < 1.5:
            return 0.05
        delta_score = min(0.5, max(0.0, (delta - 2.0) / 6.0))
        range_score = 0.3 if 34.0 <= obj <= 39.0 else 0.15
        return min(1.0, max(0.0, delta_score + range_score + 0.2))

    assert calc_confidence(24.0, 36.6) >= 0.90
    assert calc_confidence(25.0, 25.5) == 0.05
    assert calc_confidence(24.0, 24.5) == 0.0
    assert calc_confidence(24.0, 50.0) == 0.0


def test_mock_mqtt_client_lifecycle():
    client = MockMqttClient()
    assert client.is_connected() is False

    assert client.connect() is True
    assert client.is_connected() is True
    assert len(client.published_messages) == 1
    assert client.published_messages[0]["topic"] == TOPIC_STATUS
    assert client.published_messages[0]["payload"] == "online"

    assert client.subscribe(TOPIC_CMD_DISPENSE) is True
    assert TOPIC_CMD_DISPENSE in client.subscriptions

    client.disconnect()
    assert client.is_connected() is False
    assert client.published_messages[-1]["topic"] == TOPIC_STATUS
    assert client.published_messages[-1]["payload"] == "offline"


def test_mock_mqtt_telemetry_publication():
    sim = FirmwareSimulator(include_temp=True, include_dispenser=True)
    client = sim.create_mock_publisher()
    client.connect()

    ok = sim.publish_telemetry(client)
    assert ok is True
    assert len(client.published_messages) == 2

    msg = client.published_messages[1]
    assert msg["topic"] == TOPIC_VITALS_PROCESSED
    payload = json.loads(msg["payload"])
    assert "seq" in payload
    assert "ppg" in payload
    assert "ecg" in payload
    assert "temp" in payload
    assert "dispenser" in payload


def test_mock_mqtt_raw_waveform_batch_serialization():
    sim = FirmwareSimulator()
    client = sim.create_mock_publisher()
    client.connect()

    ok = sim.publish_waveform(client, sample_count=32)
    assert ok is True

    raw_msg = client.published_messages[-1]
    assert raw_msg["topic"] == TOPIC_VITALS_RAW
    data = raw_msg["payload"]
    assert isinstance(data, bytes)
    assert len(data) == 16 + (32 * 11)

    magic0, magic1, ver, seq, ts, interval, count = struct.unpack_from("<BBHIIHH", data, 0)
    assert magic0 == 0xAA
    assert magic1 == 0x55
    assert ver == 1
    assert count == 32
    assert interval == 20

    offset = 16
    for _ in range(count):
        ecg, ir, red, flags = struct.unpack_from("<HIIB", data, offset)
        assert 0 <= ecg <= 4095
        assert ir >= 200000
        assert red >= 200000
        assert flags & 0x01
        offset += 11


def test_mock_mqtt_event_publication():
    sim = FirmwareSimulator()
    client = sim.create_mock_publisher()
    client.connect()

    ok = sim.publish_event(client, "BOOT", "esp32_started")
    assert ok is True

    event_msg = client.published_messages[-1]
    assert event_msg["topic"] == TOPIC_VITALS_EVENTS
    payload = json.loads(event_msg["payload"])
    assert payload["event"] == "BOOT"
    assert payload["details"] == "esp32_started"
    assert "ts" in payload


def test_mock_mqtt_command_dispatch():
    sim = FirmwareSimulator(include_dispenser=True)
    client = sim.create_mock_publisher()
    client.connect()

    assert client.handle_command(TOPIC_CMD_DISPENSE, '{"cmd":"dispense","compartment":5}', sim) is True
    assert sim.current_compartment == 5

    assert client.handle_command(TOPIC_CMD_DISPENSE, '{"cmd":"home"}', sim) is True
    assert sim.current_compartment == 0

    assert client.handle_command(TOPIC_CMD_DISPENSE, '{"cmd":"stop"}', sim) is True
    assert sim.dispenser_moving is False

    sim.trigger_stall()
    assert sim.dispenser_stalled is True
    assert client.handle_command(TOPIC_CMD_DISPENSE, '{"cmd":"clear"}', sim) is True
    assert sim.dispenser_stalled is False


def test_telemetry_ring_buffer_semantics():
    capacity = 10
    queue = deque(maxlen=capacity)

    for i in range(15):
        if len(queue) == capacity:
            queue.popleft()
        queue.append(i)

    assert len(queue) == 10
    assert list(queue) == list(range(5, 15))

    flushed = []
    batch_size = 4
    while queue and len(flushed) < batch_size:
        flushed.append(queue.popleft())

    assert flushed == [5, 6, 7, 8]
    assert len(queue) == 6


def test_telemetry_rate_limiter_logic():
    interval_ms = 500
    last_publish_ms = 0

    def can_publish(now_ms: int) -> bool:
        nonlocal last_publish_ms
        if last_publish_ms == 0 or (now_ms - last_publish_ms) >= interval_ms:
            last_publish_ms = now_ms
            return True
        return False

    assert can_publish(100) is True
    assert can_publish(200) is False
    assert can_publish(550) is False
    assert can_publish(600) is True
    assert can_publish(700) is False
    assert can_publish(1100) is True



