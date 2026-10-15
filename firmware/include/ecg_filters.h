#ifndef ECG_FILTERS_H
#define ECG_FILTERS_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

template <typename T, uint16_t Capacity = 128>
class ECGRingBuffer {
public:
    ECGRingBuffer() : head(0), tail(0), count(0) {}

    void push(T value) {
        buffer[head] = value;
        head = (head + 1) % Capacity;
        if (count < Capacity) {
            count++;
        } else {
            tail = (tail + 1) % Capacity;
        }
    }

    bool pop(T& out_val) {
        if (count == 0) {
            return false;
        }
        out_val = buffer[tail];
        tail = (tail + 1) % Capacity;
        count--;
        return true;
    }

    T get(uint16_t index) const {
        if (index >= count) {
            return T();
        }
        uint16_t actual_idx = (tail + index) % Capacity;
        return buffer[actual_idx];
    }

    T latest() const {
        if (count == 0) {
            return T();
        }
        uint16_t idx = (head == 0) ? (Capacity - 1) : (head - 1);
        return buffer[idx];
    }

    uint16_t size() const {
        return count;
    }

    uint16_t capacity() const {
        return Capacity;
    }

    bool is_full() const {
        return count == Capacity;
    }

    bool is_empty() const {
        return count == 0;
    }

    void clear() {
        head = 0;
        tail = 0;
        count = 0;
    }

private:
    T buffer[Capacity];
    uint16_t head;
    uint16_t tail;
    uint16_t count;
};

class ButterworthHighPassFilter {
public:
    ButterworthHighPassFilter() : x1(0.0f), x2(0.0f), y1(0.0f), y2(0.0f) {}

    float step(float input) {
        float output = b0 * input + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1;
        x1 = input;
        y2 = y1;
        y1 = output;
        return output;
    }

    void reset() {
        x1 = 0.0f;
        x2 = 0.0f;
        y1 = 0.0f;
        y2 = 0.0f;
    }

private:
    static constexpr float b0 = 0.99115360f;
    static constexpr float b1 = -1.98230719f;
    static constexpr float b2 = 0.99115360f;
    static constexpr float a1 = -1.98222893f;
    static constexpr float a2 = 0.98238545f;

    float x1;
    float x2;
    float y1;
    float y2;
};

#endif
