# plastic-nurse

A modular assistive medical droid built for telemetry ingestion, guided patient routines, and teleoperation without thread blocking or runaway hardware.

We inherited a legacy demo codebase built around blocking sleep loops and synthetic data. Instead of trying to patch a brittle prototype, we kept the physical chassis, pin mappings, and media assets, and rebuilt the entire software stack from the ground up.

---

## What It Does

* Vitals Telemetry: Ingests indicative heart rate, SpO2, and single-lead ECG telemetry. Displays raw measurements and historical trends without automated medical diagnosis.
* Patient Interaction: Fully offline speech-to-text and neural text-to-speech tied to an on-screen state machine for guided routines.
* Motion and Hardware: Non-blocking teleoperation with watchdog auto-stop timers, ultrasonic obstacle interlocks, and an asynchronous door actuator state machine.

---

## System Architecture

Split into three independent layers to allow parallel development without needing the physical Raspberry Pi:

* The Nervous System (`firmware/`): Embedded C++ on ESP32 using PlatformIO. Samples sensors at fixed intervals, applies basic digital filtering, and publishes JSON payloads over MQTT.
* The Brain (`core/`): Asynchronous Python 3.11 and FastAPI service running on the Raspberry Pi. Houses the Hardware Abstraction Layer (with mock backends for local testing on Windows and Linux), SQLite storage via SQLModel, JWT security, and WebSocket channels.
* The Face (`ui/`): Touchscreen interface built with React, Vite, and TypeScript. Runs in full-screen Chromium kiosk mode with touch-first controls.

---

## Core Rules

1. Assistive, Not Diagnostic: Hobby sensors are not calibrated clinical instruments. The UI displays readings as indicative records and prompts users to consult healthcare professionals.
2. Hardware Abstraction: All code interacting with GPIO, cameras, or motors must route through a mock backend so the entire stack can be tested locally without physical hardware.
3. Non-Blocking Event Loop: Any operation running longer than 200 ms must execute in a background task and stream status updates over WebSockets.

---

## Credits & Acknowledgments

* Original Prototype: Gautam (Senior Lead) and `palceholdr` for the initial chassis construction, baseline wiring, and early proof of concept.
* Faculty Mentorship: `place`, `holderlaplace` for project guidance and lab support.
* Current Maintainers: Anirudh Ramasubramanian and Irfan Ul Haq (Rebuild architecture, async core, firmware, and UI).