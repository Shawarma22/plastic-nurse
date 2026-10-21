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
    FLAG_BATTERY_LOW = 0x10,
    FLAG_TEMP_CONNECTED = 0x20,
    FLAG_TEMP_TARGET_DETECTED = 0x40,
    FLAG_DISPENSER_ACTIVE = 0x80
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
    float filtered_signal;
    float bpm;
    float confidence;
    bool leads_off;
};

struct Mlx90614Data {
    float ambient_c;
    float object_c;
    float confidence;
    bool target_present;
};

struct StepperStatusData {
    uint8_t current_compartment;
    uint8_t target_compartment;
    bool is_moving;
    bool is_homed;
    bool stall_detected;
};

struct SensorPacket {
    uint32_t sequence_id;
    uint32_t timestamp_ms;
    Max30102Data ppg;
    Ad8232Data ecg;
    Mlx90614Data temp;
    StepperStatusData dispenser;
    uint16_t battery_mv;
    uint8_t status_flags;
};

static constexpr uint8_t WAVEFORM_MAGIC_0 = 0xAA;
static constexpr uint8_t WAVEFORM_MAGIC_1 = 0x55;
static constexpr uint16_t WAVEFORM_BATCH_VERSION = 1;
static constexpr size_t WAVEFORM_BATCH_MAX_SAMPLES = 32;

#pragma pack(push, 1)
struct WaveformSample {
    uint16_t ecg_raw;
    uint32_t ir_raw;
    uint32_t red_raw;
    uint8_t flags;
};

struct WaveformBatch {
    uint8_t magic[2];
    uint16_t version;
    uint32_t batch_seq;
    uint32_t start_timestamp_ms;
    uint16_t sample_interval_ms;
    uint16_t sample_count;
    WaveformSample samples[WAVEFORM_BATCH_MAX_SAMPLES];
};
#pragma pack(pop)

#endif
