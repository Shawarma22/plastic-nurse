#ifndef TELEMETRY_RING_BUFFER_H
#define TELEMETRY_RING_BUFFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "sensor_types.h"
#include "config.h"

template <size_t Capacity = MQTT_OFFLINE_QUEUE_CAPACITY>
class TelemetryRingBuffer {
public:
    TelemetryRingBuffer();

    bool push(const SensorPacket& packet);
    bool pop(SensorPacket& packet);
    bool peek(SensorPacket& packet) const;
    void clear();

    bool is_empty() const;
    bool is_full() const;
    size_t size() const;
    size_t capacity() const;
    uint32_t get_overflow_count() const;

private:
    SensorPacket buffer[Capacity];
    size_t head;
    size_t tail;
    size_t count;
    uint32_t overflow_count;
};

#endif
