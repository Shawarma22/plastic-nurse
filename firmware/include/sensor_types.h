#ifndef SENSOR_TYPES_H
#define SENSOR_TYPES_H

#include <stdint.h>
#include <stdbool.h>

enum SensorStatusFlag : uint8_t {
    FLAG_NONE = 0x00,
    FLAG_PPG_CONNECTED = 0x01,
    FLAG_ECG_CONNECTED = 0x02,
    FLAG_PPG_FINGER_DETECTED = 0x04,
    FLAG_ECG_LEAD_OFF = 0x08,
    FLAG_BATTERY_LOW = 0x10
};

struct Max30102Data {
    uint32_t ir_raw;
    uint32_t red_raw;
    float bpm;
    float spo2;
    float confidence;
    bool finger_detected;
};

struct Ad8232Data {
    uint16_t raw_signal;
    bool leads_off;
};

struct SensorPacket {
    uint32_t sequence_id;
    uint32_t timestamp_ms;
    Max30102Data ppg;
    Ad8232Data ecg;
    uint16_t battery_mv;
    uint8_t status_flags;
};

#endif
