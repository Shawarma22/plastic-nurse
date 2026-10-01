import base64
from fastapi.testclient import TestClient
from app.perception.audio import MockAudioSource
from app.perception.stt import (
    MockSpeechRecognizer,
    VoskSpeechRecognizer,
    SpeechTranscriptResult
)

def test_mock_audio_source():
    source = MockAudioSource(sample_rate=16000)
    assert source.is_active is False
    assert source.read_chunk() == b""

    source.start()
    assert source.is_active is True
    chunk = source.read_chunk(4096)
    assert len(chunk) == 4096

    source.feed_phrase("test phrase")
    assert source.pop_phrase() == "test phrase"
    assert source.pop_phrase() is None

    source.stop()
    assert source.is_active is False
    assert source.read_chunk() == b""

def test_mock_speech_recognizer():
    recognizer = MockSpeechRecognizer(predefined_transcripts=["hello nurse", "open door"])
    empty_res = recognizer.accept_waveform(b"")
    assert empty_res is None

    partial_res = recognizer.accept_waveform(b"x" * 1024)
    assert partial_res is not None
    assert partial_res.is_final is False

    final_res = recognizer.accept_waveform(b"x" * 8192)
    assert final_res is not None
    assert final_res.is_final is True
    assert final_res.transcript == "hello nurse"

    res_flush = recognizer.get_final_result()
    assert isinstance(res_flush, SpeechTranscriptResult)
    assert res_flush.transcript == "hello nurse"

    recognizer.reset()
    assert recognizer._buffer_size == 0

def test_vosk_speech_recognizer_fallback():
    recognizer = VoskSpeechRecognizer(model_path="nonexistent_vosk_dir")
    assert recognizer._fallback is not None

    res = recognizer.accept_waveform(b"x" * 8192)
    assert res is not None
    assert res.is_final is True

    final_res = recognizer.get_final_result()
    assert final_res.is_final is True

def test_stt_api_endpoint(client: TestClient, operator_token: str):
    unauth_res = client.post("/api/v1/perception/stt/transcribe")
    assert unauth_res.status_code == 401

    headers = {"Authorization": f"Bearer {operator_token}"}
    sim_res = client.post(
        "/api/v1/perception/stt/transcribe",
        json={"simulate_phrase": "bring water"},
        headers=headers
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["transcript"] == "bring water"
    assert sim_data["is_final"] is True

    dummy_pcm = b"\x00" * 8192
    b64_audio = base64.b64encode(dummy_pcm).decode("utf-8")
    stream_res = client.post(
        "/api/v1/perception/stt/transcribe",
        json={"audio_base64": b64_audio},
        headers=headers
    )
    assert stream_res.status_code == 200
    stream_data = stream_res.json()
    assert "transcript" in stream_data
    assert "is_final" in stream_data
