import time
from fastapi.testclient import TestClient
from app.services.tts_service import TtsService, AudioOutputState


def test_tts_service_instantiation(tmp_path):
    service = TtsService()
    assert service.get_state() == AudioOutputState.IDLE
    assert service.is_busy() is False
    assert service.cache_dir.exists()


def test_tts_clean_text_and_chunking():
    service = TtsService()
    raw = "   Patient   observed in room 12!  Alert: vitals normal...   "
    cleaned = service.clean_text(raw)
    assert "  " not in cleaned
    assert "room 12" in cleaned

    long_text = (
        "This is the first segment of observation data. "
        "Here is the second segment with vital measurement information, and subsequent sensor logs. "
        "Finally this completes the auditory broadcast sequence."
    )
    chunks = service.chunk_text(long_text, max_chunk_words=10)
    assert len(chunks) >= 3
    for chunk in chunks:
        assert len(chunk.split()) <= 15


def test_mock_wav_synthesis_and_caching(tmp_path):
    service = TtsService()
    wav_bytes = service.synthesize_mock("measurement update 120 over 80")
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]

    cached = service.get_cached_audio("measurement update 120 over 80", engine="mock")
    assert cached == wav_bytes
    assert service.is_cached("measurement update 120 over 80", engine="mock")

    cleared = service.clear_cache()
    assert cleared >= 1


def test_piper_and_espeak_availability():
    service = TtsService()
    piper_ok = service.is_piper_available()
    espeak_ok = service.is_espeak_available()
    assert isinstance(piper_ok, bool)
    assert isinstance(espeak_ok, bool)


def test_engine_fallback_chain():
    service = TtsService()
    data, engine_used = service.synthesize("vital signals recorded", preferred_engine="piper")
    assert len(data) > 0
    assert engine_used in ("piper", "espeak", "mock")

    metrics = service.get_metrics()
    assert "state" in metrics
    assert "fallback_count" in metrics
    assert metrics["last_used_engine"] == engine_used


def test_speech_queue_worker_execution():
    service = TtsService()
    service.start()
    try:
        uid = service.enqueue_speech("system operational notification")
        assert uid is not None
        time.sleep(0.4)
        metrics = service.get_metrics()
        assert metrics["total_utterances"] >= 1
    finally:
        service.stop_worker()


def test_tts_interrupt_and_stop():
    service = TtsService()
    service.start()
    try:
        service.enqueue_speech("first long observation message")
        service.enqueue_speech("second observation message")
        service.stop()
        assert service.get_state() == AudioOutputState.IDLE
        assert service._queue.empty()
    finally:
        service.stop_worker()


def test_tts_cancel_single_utterance():
    service = TtsService()
    uid = service.enqueue_speech("cancelable utterance")
    cancelled = service.cancel_utterance(uid)
    assert isinstance(cancelled, bool)


def test_tts_rest_endpoints(client: TestClient, operator_token: str):
    headers = {"Authorization": f"Bearer {operator_token}"}

    res_status = client.get("/api/v1/tts/status", headers=headers)
    assert res_status.status_code == 200
    data = res_status.json()
    assert "state" in data
    assert "queue_size" in data

    res_speak = client.post(
        "/api/v1/tts/speak",
        json={"text": "heart rate signal steady at 72 bpm", "engine": "mock"},
        headers=headers,
    )
    assert res_speak.status_code == 200
    speak_data = res_speak.json()
    assert speak_data["status"] == "queued"
    assert "utterance_id" in speak_data

    res_synth = client.post(
        "/api/v1/tts/synthesize",
        json={"text": "direct audio render test", "engine": "mock"},
        headers=headers,
    )
    assert res_synth.status_code == 200
    assert res_synth.headers["content-type"] == "audio/wav"
    assert res_synth.content.startswith(b"RIFF")

    res_cancel = client.post(
        "/api/v1/tts/cancel",
        json={"utterance_id": speak_data["utterance_id"]},
        headers=headers,
    )
    assert res_cancel.status_code == 200

    res_stop = client.post("/api/v1/tts/stop", headers=headers)
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "stopped"

    res_cache = client.delete("/api/v1/tts/cache", headers=headers)
    assert res_cache.status_code == 200
    assert "cleared_files" in res_cache.json()
