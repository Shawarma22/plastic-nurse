import struct
from app.perception.audio_buffer import AudioRingBuffer
from app.perception.energy_vad import EnergyVAD
from app.perception.wake_mock import MockWakeWordDetector
from app.perception.keyword_spotter import KeywordSpotter

def test_audio_ring_buffer_basic():
    buf = AudioRingBuffer(capacity_bytes=100)
    assert buf.size() == 0
    assert buf.is_full() is False
    assert buf.read_recent() == b""

    buf.write(b"hello")
    assert buf.size() == 5
    assert buf.read_recent(5) == b"hello"

    buf.write(b" world")
    assert buf.size() == 11
    assert buf.read_recent(11) == b"hello world"
    assert buf.read_recent(5) == b"world"

    buf.clear()
    assert buf.size() == 0
    assert buf.read_recent() == b""

def test_audio_ring_buffer_overflow():
    buf = AudioRingBuffer(capacity_bytes=10)
    buf.write(b"0123456789abcdef")
    assert buf.size() == 10
    assert buf.is_full() is True
    assert buf.read_recent() == b"6789abcdef"

    buf.write(b"XYZ")
    assert buf.size() == 10
    assert buf.read_recent() == b"9abcdefXYZ"

def test_energy_vad():
    vad = EnergyVAD(threshold=200.0)
    assert vad.get_threshold() == 200.0

    silence = b"\x00\x00" * 100
    assert vad.calculate_rms(silence) == 0.0
    assert vad.is_speech(silence) is False

    loud_samples = [10000] * 100
    loud_bytes = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
    rms = vad.calculate_rms(loud_bytes)
    assert rms == 10000.0
    assert vad.is_speech(loud_bytes) is True

    vad.set_threshold(15000.0)
    assert vad.is_speech(loud_bytes) is False

def test_mock_wake_word_detector():
    det = MockWakeWordDetector(wake_word="hey droid", auto_trigger_after_chunks=3)
    assert det.is_active() is True

    assert det.process_audio_chunk(b"chunk1").detected is False
    assert det.process_audio_chunk(b"chunk2").detected is False
    res3 = det.process_audio_chunk(b"chunk3")
    assert res3.detected is True
    assert res3.wake_word == "hey droid"
    assert res3.confidence == 0.95

    det.trigger_next(confidence=0.99)
    res_forced = det.process_audio_chunk(b"chunk_forced")
    assert res_forced.detected is True
    assert res_forced.confidence == 0.99

    det.reset()
    assert det.process_audio_chunk(b"chunk_after_reset").detected is False

def test_keyword_spotter():
    spotter = KeywordSpotter(wake_word="hey droid", vad_threshold=100.0)
    assert spotter.is_active() is True

    silence = b"\x00\x00" * 50
    assert spotter.process_audio_chunk(silence).detected is False

    spotter.trigger_test_wake(0.92)
    loud_samples = [1000] * 50
    loud_bytes = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
    res = spotter.process_audio_chunk(loud_bytes)
    assert res.detected is True
    assert res.confidence == 0.92

    spotter.reset()
    assert spotter.ring_buffer.size() == 0
