#include "packet_serializer.h"
#include <ArduinoJson.h>
#include <string.h>

size_t serializeSensorPacket(const SensorPacket& packet, char* buffer, size_t bufferSize) {
    StaticJsonDocument<512> doc;

    doc["seq"] = packet.sequence_id;
    doc["ts"] = packet.timestamp_ms;

    JsonObject ppg = doc.createNestedObject("ppg");
    ppg["ir"] = packet.ppg.ir_raw;
    ppg["red"] = packet.ppg.red_raw;
    ppg["bpm"] = packet.ppg.bpm;
    ppg["spo2"] = packet.ppg.spo2;
    ppg["conf"] = packet.ppg.confidence;
    ppg["finger"] = packet.ppg.finger_detected;

    JsonObject ecg = doc.createNestedObject("ecg");
    ecg["raw"] = packet.ecg.raw_signal;
    ecg["lead_off"] = packet.ecg.leads_off;

    JsonObject temp = doc.createNestedObject("temp");
    temp["amb"] = packet.temp.ambient_c;
    temp["obj"] = packet.temp.object_c;
    temp["conf"] = packet.temp.confidence;
    temp["target"] = packet.temp.target_present;

    JsonObject dispenser = doc.createNestedObject("dispenser");
    dispenser["comp"] = packet.dispenser.current_compartment;
    dispenser["target"] = packet.dispenser.target_compartment;
    dispenser["moving"] = packet.dispenser.is_moving;
    dispenser["homed"] = packet.dispenser.is_homed;
    dispenser["stall"] = packet.dispenser.stall_detected;

    doc["bat"] = packet.battery_mv;
    doc["status"] = packet.status_flags;

    return serializeJson(doc, buffer, bufferSize);
}

bool deserializeSensorPacket(const char* json, SensorPacket& packet) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, json);
    if (error) {
        return false;
    }

    packet.sequence_id = doc["seq"] | 0;
    packet.timestamp_ms = doc["ts"] | 0;

    JsonObject ppg = doc["ppg"];
    if (!ppg.isNull()) {
        packet.ppg.ir_raw = ppg["ir"] | 0;
        packet.ppg.red_raw = ppg["red"] | 0;
        packet.ppg.bpm = ppg["bpm"] | 0.0f;
        packet.ppg.spo2 = ppg["spo2"] | 0.0f;
        packet.ppg.confidence = ppg["conf"] | 0.0f;
        packet.ppg.finger_detected = ppg["finger"] | false;
    }

    JsonObject ecg = doc["ecg"];
    if (!ecg.isNull()) {
        packet.ecg.raw_signal = ecg["raw"] | 0;
        packet.ecg.leads_off = ecg["lead_off"] | false;
    }

    JsonObject temp = doc["temp"];
    if (!temp.isNull()) {
        packet.temp.ambient_c = temp["amb"] | 0.0f;
        packet.temp.object_c = temp["obj"] | 0.0f;
        packet.temp.confidence = temp["conf"] | 0.0f;
        packet.temp.target_present = temp["target"] | false;
    }

    JsonObject dispenser = doc["dispenser"];
    if (!dispenser.isNull()) {
        packet.dispenser.current_compartment = dispenser["comp"] | 0;
        packet.dispenser.target_compartment = dispenser["target"] | 0;
        packet.dispenser.is_moving = dispenser["moving"] | false;
        packet.dispenser.is_homed = dispenser["homed"] | false;
        packet.dispenser.stall_detected = dispenser["stall"] | false;
    }

    packet.battery_mv = doc["bat"] | 0;
    packet.status_flags = doc["status"] | 0;

    return true;
}

size_t serializeWaveformBatch(const WaveformBatch& batch, uint8_t* buffer, size_t bufferSize) {
    if (buffer == nullptr || batch.sample_count > WAVEFORM_BATCH_MAX_SAMPLES) {
        return 0;
    }
    size_t payload_len = 16 + (batch.sample_count * sizeof(WaveformSample));
    if (bufferSize < payload_len) {
        return 0;
    }
    uint8_t m0 = WAVEFORM_MAGIC_0;
    uint8_t m1 = WAVEFORM_MAGIC_1;
    uint16_t ver = WAVEFORM_BATCH_VERSION;
    memcpy(buffer, &m0, 1);
    memcpy(buffer + 1, &m1, 1);
    memcpy(buffer + 2, &ver, sizeof(ver));
    memcpy(buffer + 4, &batch.batch_seq, sizeof(batch.batch_seq));
    memcpy(buffer + 8, &batch.start_timestamp_ms, sizeof(batch.start_timestamp_ms));
    memcpy(buffer + 12, &batch.sample_interval_ms, sizeof(batch.sample_interval_ms));
    memcpy(buffer + 14, &batch.sample_count, sizeof(batch.sample_count));
    if (batch.sample_count > 0) {
        memcpy(buffer + 16, batch.samples, batch.sample_count * sizeof(WaveformSample));
    }
    return payload_len;
}

bool deserializeWaveformBatch(const uint8_t* buffer, size_t length, WaveformBatch& batch) {
    if (buffer == nullptr || length < 16) {
        return false;
    }
    if (buffer[0] != WAVEFORM_MAGIC_0 || buffer[1] != WAVEFORM_MAGIC_1) {
        return false;
    }
    uint16_t version = 0;
    memcpy(&version, buffer + 2, sizeof(version));
    if (version != WAVEFORM_BATCH_VERSION) {
        return false;
    }
    memcpy(&batch.magic[0], buffer, 2);
    batch.version = version;
    memcpy(&batch.batch_seq, buffer + 4, sizeof(batch.batch_seq));
    memcpy(&batch.start_timestamp_ms, buffer + 8, sizeof(batch.start_timestamp_ms));
    memcpy(&batch.sample_interval_ms, buffer + 12, sizeof(batch.sample_interval_ms));
    memcpy(&batch.sample_count, buffer + 14, sizeof(batch.sample_count));

    if (batch.sample_count > WAVEFORM_BATCH_MAX_SAMPLES) {
        return false;
    }
    size_t expected_len = 16 + (batch.sample_count * sizeof(WaveformSample));
    if (length < expected_len) {
        return false;
    }
    if (batch.sample_count > 0) {
        memcpy(batch.samples, buffer + 16, batch.sample_count * sizeof(WaveformSample));
    }
    return true;
}
