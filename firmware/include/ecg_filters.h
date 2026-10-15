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

class ButterworthLowPassFilter {
public:
    ButterworthLowPassFilter() : x1(0.0f), x2(0.0f), y1(0.0f), y2(0.0f) {}

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
    static constexpr float b0 = 0.14532388f;
    static constexpr float b1 = 0.29064777f;
    static constexpr float b2 = 0.14532388f;
    static constexpr float a1 = -0.67102909f;
    static constexpr float a2 = 0.25232463f;

    float x1;
    float x2;
    float y1;
    float y2;
};

class ECGBandpassFilter {
public:
    ECGBandpassFilter() {}

    float step(float input) {
        float hp = hp_filter.step(input);
        return lp_filter.step(hp);
    }

    void reset() {
        hp_filter.reset();
        lp_filter.reset();
    }

private:
    ButterworthHighPassFilter hp_filter;
    ButterworthLowPassFilter lp_filter;
};

class PanTompkinsDerivative {
public:
    PanTompkinsDerivative() : x1(0.0f), x2(0.0f), x3(0.0f), x4(0.0f) {}

    float step(float input) {
        float output = (2.0f * input + x1 - x3 - 2.0f * x4) * 0.125f;
        x4 = x3;
        x3 = x2;
        x2 = x1;
        x1 = input;
        return output;
    }

    void reset() {
        x1 = 0.0f;
        x2 = 0.0f;
        x3 = 0.0f;
        x4 = 0.0f;
    }

private:
    float x1;
    float x2;
    float x3;
    float x4;
};

template <uint8_t WindowSize = 32>
class MovingWindowIntegrator {
public:
    MovingWindowIntegrator() : index(0), count(0), sum(0.0f) {
        for (uint8_t i = 0; i < WindowSize; ++i) {
            buffer[i] = 0.0f;
        }
    }

    float step(float input) {
        float squared = input * input;
        sum -= buffer[index];
        buffer[index] = squared;
        sum += squared;
        index = (index + 1) % WindowSize;
        if (count < WindowSize) {
            count++;
        }
        return sum / static_cast<float>(count);
    }

    float get_energy() const {
        return (count == 0) ? 0.0f : (sum / static_cast<float>(count));
    }

    void reset() {
        index = 0;
        count = 0;
        sum = 0.0f;
        for (uint8_t i = 0; i < WindowSize; ++i) {
            buffer[i] = 0.0f;
        }
    }

private:
    float buffer[WindowSize];
    uint8_t index;
    uint8_t count;
    float sum;
};

class ECGPeakDetector {
public:
    ECGPeakDetector(uint16_t sample_rate_hz = 250)
        : sample_rate(sample_rate_hz),
          refractory_samples(sample_rate_hz / 5),
          samples_since_peak(0),
          spki(0.0f),
          npki(0.0f),
          threshold(0.0f),
          prev_val(0.0f),
          prev_slope(0.0f),
          is_initialized(false) {}

    bool step(float energy, float& out_peak_val) {
        samples_since_peak++;

        float slope = energy - prev_val;
        bool is_local_peak = (prev_slope > 0.0f && slope <= 0.0f);
        float peak_candidate = prev_val;
        prev_slope = slope;
        prev_val = energy;

        if (!is_local_peak) {
            return false;
        }

        if (!is_initialized) {
            spki = peak_candidate;
            npki = peak_candidate * 0.1f;
            threshold = npki + 0.25f * (spki - npki);
            is_initialized = true;
            return false;
        }

        if (samples_since_peak > refractory_samples && peak_candidate > threshold) {
            spki = 0.125f * peak_candidate + 0.875f * spki;
            threshold = npki + 0.25f * (spki - npki);
            samples_since_peak = 0;
            out_peak_val = peak_candidate;
            return true;
        } else {
            npki = 0.125f * peak_candidate + 0.875f * npki;
            threshold = npki + 0.25f * (spki - npki);
            return false;
        }
    }

    float get_threshold() const {
        return threshold;
    }

    float get_spki() const {
        return spki;
    }

    float get_npki() const {
        return npki;
    }

    void reset() {
        samples_since_peak = 0;
        spki = 0.0f;
        npki = 0.0f;
        threshold = 0.0f;
        prev_val = 0.0f;
        prev_slope = 0.0f;
        is_initialized = false;
    }

private:
    uint16_t sample_rate;
    uint16_t refractory_samples;
    uint32_t samples_since_peak;
    float spki;
    float npki;
    float threshold;
    float prev_val;
    float prev_slope;
    bool is_initialized;
};

#endif
