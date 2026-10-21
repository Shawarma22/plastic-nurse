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

template <size_t Capacity>
TelemetryRingBuffer<Capacity>::TelemetryRingBuffer()
    : head(0), tail(0), count(0), overflow_count(0) {}

template <size_t Capacity>
bool TelemetryRingBuffer<Capacity>::push(const SensorPacket& packet) {
    if (Capacity == 0) {
        return false;
    }
    bool overflow = (count == Capacity);
    if (overflow) {
        tail = (tail + 1) % Capacity;
        overflow_count++;
    } else {
        count++;
    }
    buffer[head] = packet;
    head = (head + 1) % Capacity;
    return !overflow;
}

template <size_t Capacity>
bool TelemetryRingBuffer<Capacity>::pop(SensorPacket& packet) {
    if (count == 0) {
        return false;
    }
    packet = buffer[tail];
    tail = (tail + 1) % Capacity;
    count--;
    return true;
}

template <size_t Capacity>
bool TelemetryRingBuffer<Capacity>::peek(SensorPacket& packet) const {
    if (count == 0) {
        return false;
    }
    packet = buffer[tail];
    return true;
}

template <size_t Capacity>
void TelemetryRingBuffer<Capacity>::clear() {
    head = 0;
    tail = 0;
    count = 0;
}

template <size_t Capacity>
bool TelemetryRingBuffer<Capacity>::is_empty() const {
    return (count == 0);
}

template <size_t Capacity>
bool TelemetryRingBuffer<Capacity>::is_full() const {
    return (count == Capacity);
}

template <size_t Capacity>
size_t TelemetryRingBuffer<Capacity>::size() const {
    return count;
}

template <size_t Capacity>
size_t TelemetryRingBuffer<Capacity>::capacity() const {
    return Capacity;
}

template <size_t Capacity>
uint32_t TelemetryRingBuffer<Capacity>::get_overflow_count() const {
    return overflow_count;
}

#endif
