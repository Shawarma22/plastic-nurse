#include "packet_serializer.h"
#include <ArduinoJson.h>

size_t serializeSensorPacket(const SensorPacket& packet, char* buffer, size_t bufferSize) {
    StaticJsonDocument<256> doc;

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

    doc["bat"] = packet.battery_mv;
    doc["status"] = packet.status_flags;

    return serializeJson(doc, buffer, bufferSize);
}

bool deserializeSensorPacket(const char* json, SensorPacket& packet) {
    StaticJsonDocument<256> doc;
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

    packet.battery_mv = doc["bat"] | 0;
    packet.status_flags = doc["status"] | 0;

    return true;
}
