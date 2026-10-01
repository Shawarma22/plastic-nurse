import pytest
import numpy as np
from app.perception.tflite_runner import TFLiteInferenceRunner
from app.perception.benchmark import run_inference_benchmark, format_benchmark_report

def test_tflite_runner_mock_mode():
    runner = TFLiteInferenceRunner(model_path="nonexistent_model.tflite")
    info = runner.get_model_info()
    assert info["loaded"] is False
    assert info["is_quantized"] is True
    assert info["input_shape"] == [1, 48, 48, 1]
    assert info["output_shape"] == [1, 7]

def test_tflite_runner_preprocess():
    runner = TFLiteInferenceRunner()
    with pytest.raises(ValueError):
        runner.preprocess(np.array([]))

    sample_bgr = np.zeros((100, 100, 3), dtype=np.uint8)
    tensor = runner.preprocess(sample_bgr, target_size=(48, 48), grayscale=True)
    assert tensor.shape == (1, 48, 48, 1)

    sample_gray = np.zeros((64, 64), dtype=np.uint8)
    tensor_gray = runner.preprocess(sample_gray, target_size=(48, 48), grayscale=True)
    assert tensor_gray.shape == (1, 48, 48, 1)

def test_tflite_runner_inference():
    runner = TFLiteInferenceRunner()
    dummy_input = np.zeros((1, 48, 48, 1), dtype=np.int8)
    output = runner.infer(dummy_input)
    assert output.shape == (1, 7)
    assert np.isclose(np.sum(output), 1.0, atol=1e-5)

def test_run_inference_benchmark():
    runner = TFLiteInferenceRunner()
    metrics = run_inference_benchmark(runner, iterations=10, dummy_shape=(48, 48, 1))
    assert metrics.iterations == 10
    assert metrics.total_time_ms > 0.0
    assert metrics.mean_latency_ms > 0.0
    assert metrics.min_latency_ms <= metrics.mean_latency_ms <= metrics.max_latency_ms
    assert metrics.p95_latency_ms >= metrics.min_latency_ms
    assert metrics.fps > 0.0

def test_format_benchmark_report():
    runner = TFLiteInferenceRunner()
    metrics = run_inference_benchmark(runner, iterations=5, dummy_shape=(48, 48, 1))
    report = format_benchmark_report(metrics, runner.get_model_info())
    assert "| Parameter | Value |" in report
    assert f"| Iterations | {metrics.iterations} |" in report
    assert "Mean Latency" in report
    assert "Throughput (FPS)" in report
