# ESP32 Hardware Wiring and Interface Specification

## 1. Hardware Pinout Mapping

The ESP32 DevKit V1 module interfaces with biometric sensors, indicators, and UART serial communication to the host processor.

### 1.1 MAX30102 Optical PPG Sensor (I2C)

| Sensor Pin | ESP32 GPIO | Description | Voltage Level |
|---|---|---|---|
| VIN | 3V3 | Power Supply | 3.3V DC |
| GND | GND | Ground Reference | 0V |
| SDA | GPIO 21 | I2C Data (with 4.7kΩ pull-up) | 3.3V Logic |
| SCL | GPIO 22 | I2C Clock (with 4.7kΩ pull-up) | 3.3V Logic |
| INT | GPIO 19 | Hardware Interrupt (Active Low) | 3.3V Logic |

### 1.2 AD8232 Analog Front-End (ECG)

| Sensor Pin | ESP32 GPIO | Description | Voltage Level |
|---|---|---|---|
| 3.3V | 3V3 | Regulated Power | 3.3V DC |
| GND | GND | System Ground | 0V |
| OUTPUT | GPIO 34 | Analog Signal Output (ADC1_CH6) | 0.0V - 3.3V Analog |
| LO+ | GPIO 32 | Lead-Off Detect Positive | 3.3V Logic |
| LO- | GPIO 33 | Lead-Off Detect Negative | 3.3V Logic |
| SDN | GPIO 25 | Active-Low Shutdown Control | 3.3V Logic |

### 1.3 Hardware Status Indicators

| Indicator | ESP32 GPIO | Color | Current Limiting Resistor | Default State |
|---|---|---|---|---|
| Status LED | GPIO 2 | Blue | 330Ω | 1 Hz Heartbeat Blinker |
| WiFi LED | GPIO 4 | Green | 330Ω | Off / Active Low |
| Sensor LED | GPIO 16 | Amber | 330Ω | Off / Active High on Acquisition |

---

## 2. Serial Communication Interface

- **Physical Link:** UART0 over USB / Header Pins (GPIO 1 TX, GPIO 3 RX)
- **Baud Rate:** 115200 bps
- **Data Bits:** 8
- **Parity:** None
- **Stop Bits:** 1
- **Flow Control:** None

### 2.1 Telemetry Packet Contract

Frames are transmitted as newline-delimited JSON objects matching the firmware serializer and Python telemetry simulator schema:

```json
{
  "seq": 1042,
  "ts": 52100,
  "ppg": {
    "ir": 262144,
    "red": 251020,
    "bpm": 72.4,
    "spo2": 98.6,
    "conf": 0.96,
    "finger": true
  },
  "ecg": {
    "raw": 2048,
    "lead_off": false
  },
  "bat": 4050,
  "status": 7
}
```

---

## 3. FreeRTOS Task Architecture

| Task Name | Core Affinity | Stack Size | Priority | Interval | Responsibility |
|---|---|---|---|---|---|
| `heartbeat` | Core 1 | 2048 bytes | 1 | 500 ms | Non-blocking LED status toggling |
| `telemetry` | Core 1 | 4096 bytes | 2 | 500 ms | JSON frame serialization and UART transmission |
| `sensors` | Core 0 | 4096 bytes | 3 | 10 ms / 4 ms | I2C PPG read & ADC ECG sampling routines |

---

## 4. Electrical and Safety Considerations

1. **Shared Grounding:** ESP32 ground must be common with the host Raspberry Pi 4 controller ground.
2. **ADC Attenuation:** GPIO 34 operates on ESP32 ADC1 with 11 dB input attenuation to accommodate the full 0V to 3.3V span.
3. **I2C Bus Recovery:** Hardware recovery routine clocks SCL 9 times to release bus hang states on abnormal power-cycling.
4. **Electrode Safety:** The AD8232 module utilizes battery-isolated reference rails to maintain low-leakage patient lead isolation.
