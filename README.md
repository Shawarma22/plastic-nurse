# Medical Assistive Droid (Plastic Nurse)

An autonomous edge-robotics and assistive medical droid architecture designed for inpatient support, non-blocking hardware control, and vital measurements telemetry.

## System Overview

The Medical Droid monorepo is structured around a decoupled, three-tier architecture:

- **The Nervous System (`firmware/`):** Real-time sensor acquisition and filtering running on ESP32 microcontrollers, publishing filtered telemetry over MQTT.
- **The Brain (`core/`):** Asynchronous Python/FastAPI service hosting the Hardware Abstraction Layer (HAL), SQLite persistence, JWT authentication, and WebSocket streams.
- **The Face (`ui/`):** Touchscreen kiosk interface and remote monitoring application built with React, Vite, and TypeScript.

## Architecture Principles

- **Hardware Abstraction Layer:** Uniform abstract contracts for GPIO actuators, sensors, and camera with dual support for physical hardware and local simulation mock backends.
- **Non-Blocking Execution:** Asynchronous state machines and auto-stop safety watchdogs preventing request thread blocking and hardware runaway conditions.
- **Data Security:** Stateless JWT authentication and cryptographic password hashing guarding all system endpoints.
- **Assistive Scope:** Designed for data collection, triage recording, and assistive interaction without autonomous medical diagnosis.

## Acknowledgments & Credits

This project builds upon the foundational prototype, physical hardware wiring, and domain exploration initiated by the senior batch. Special gratitude and acknowledgment to:

- **Original Project Authors & Senior Batch:** For building the initial hardware proof-of-concept, establishing sensor baseline designs, and assembling the original mechanical structure.
- **Faculty Advisor & Supervising Professor:** For continuous guidance, technical mentorship, and institutional support throughout the development and rebuild of this system.
- **Current Development & Maintenance Team:** For architecting the modular monorepo, Hardware Abstraction Layer, and asynchronous core services.
