import json
from app.hal.firmware_sim import FirmwareSimulator


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
