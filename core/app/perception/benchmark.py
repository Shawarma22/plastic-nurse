import time
from typing import Dict, Any, Tuple
import numpy as np
from pydantic import BaseModel
from app.perception.tflite_runner import TFLiteInferenceRunner

class BenchmarkMetrics(BaseModel):
    iterations: int
    total_time_ms: float
    mean_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    fps: float

def run_inference_benchmark(
    runner: TFLiteInferenceRunner,
    iterations: int = 50,
    dummy_shape: Tuple[int, int, int] = (48, 48, 1)
) -> BenchmarkMetrics:
    iterations = max(1, iterations)
    dummy_input = np.zeros((1, *dummy_shape), dtype=np.int8 if runner.is_quantized else np.float32)
    _ = runner.infer(dummy_input)
    latencies_ms = []
    start_total = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = runner.infer(dummy_input)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    total_time_ms = (time.perf_counter() - start_total) * 1000.0
    arr = np.array(latencies_ms)
    mean_lat = float(np.mean(arr))
    min_lat = float(np.min(arr))
    max_lat = float(np.max(arr))
    p95_lat = float(np.percentile(arr, 95))
    fps = round(1000.0 / mean_lat, 2) if mean_lat > 0 else 0.0
    return BenchmarkMetrics(
        iterations=iterations,
        total_time_ms=round(total_time_ms, 2),
        mean_latency_ms=round(mean_lat, 2),
        min_latency_ms=round(min_lat, 2),
        max_latency_ms=round(max_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        fps=fps
    )

def format_benchmark_report(metrics: BenchmarkMetrics, model_info: Dict[str, Any]) -> str:
    return (
        f"| Parameter | Value |\n"
        f"|---|---|\n"
        f"| Model Loaded | {model_info.get('loaded')} |\n"
        f"| Quantized | {model_info.get('is_quantized')} |\n"
        f"| Input Shape | {model_info.get('input_shape')} |\n"
        f"| Iterations | {metrics.iterations} |\n"
        f"| Mean Latency | {metrics.mean_latency_ms} ms |\n"
        f"| P95 Latency | {metrics.p95_latency_ms} ms |\n"
        f"| Min / Max Latency | {metrics.min_latency_ms} / {metrics.max_latency_ms} ms |\n"
        f"| Throughput (FPS) | {metrics.fps} FPS |\n"
    )
