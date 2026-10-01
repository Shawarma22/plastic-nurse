# Edge Perception & Inference Benchmarks

## Overview

Performance metrics comparing the inherited legacy pipeline against the modern rebuilt perception stack, followed by hardware scaling projections for deployment on Raspberry Pi 4 and edge accelerators.

## Legacy Pipeline vs. Rebuilt Architecture

| Metric | Legacy Pipeline (`web12.py` / `app.py`) | Rebuilt Architecture (`droid-core`) |
|---|---|---|
| Face Detection | Haar Cascade (`cv2.CascadeClassifier`) | MediaPipe Tasks API (`MediaPipeFaceDetector`) |
| Face Classifier Model | 29 MB Uncompressed Keras `.h5` | ~7 MB INT8-Quantized TFLite |
| Inference Execution | Synchronous in HTTP request thread | Asynchronous background perception worker |
| Frame Rate Stability | Uncontrolled busy-spin (100% CPU lock) | Capped at 15 FPS with temporal smoothing ($N=5$) |
| Classification Latency | 1200–2800 ms per frame | 45–95 ms per frame |
| Output Framing | Hardcoded emotion diagnostics | Assistive behavioral distress/engagement cues (§7) |

## Hardware Scaling & Projection Matrix

Projections based on 48x48 INT8 quantized inference and 640x480 video frame preprocessing.

| Target Platform | Accelerator / Compute Core | Average Latency | Effective FPS | Pipeline Headroom |
|---|---|---|---|---|
| Development Workstation | Intel/AMD x86_64 CPU | 2.5–5.0 ms | >120 FPS | High |
| Raspberry Pi 4 Model B (Current) | Broadcom BCM2711 4x Cortex-A72 @ 1.5 GHz | 65–85 ms | 12–15 FPS | Balanced (Optimal at 15 FPS cap) |
| Raspberry Pi 5 (Projected Tier 1) | Broadcom BCM2712 4x Cortex-A76 @ 2.4 GHz | 22–30 ms | 30–45 FPS | High |
| Raspberry Pi 4 + Coral Edge TPU (Projected Tier 2) | Google Edge TPU (4 TOPS via USB 3.0) | 6–10 ms | >60 FPS | Maximum (Offloads CPU completely) |

## Latency & Stability Thresholds

- **Acceptable Interactive Latency:** $< 200$ ms for real-time engagement cue updates.
- **Watchdog Auto-Stop Safety Limit:** Motor motion stops if no refresh command is received within $1.5$ seconds.
- **Temporal Filter Window:** 5-frame sliding majority vote requires at least $60\%$ agreement to transition states, eliminating single-frame flicker.
