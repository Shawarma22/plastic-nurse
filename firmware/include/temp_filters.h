#ifndef TEMP_FILTERS_H
#define TEMP_FILTERS_H

#include <stdint.h>
#include <stdbool.h>

static constexpr float TEMP_MIN_PLAUSIBLE_C = 30.0f;
static constexpr float TEMP_MAX_PLAUSIBLE_C = 43.0f;
static constexpr float TEMP_MAX_STEP_DELTA_C = 3.0f;

class TemperaturePlausibilityFilter {
public:
    TemperaturePlausibilityFilter()
        : min_val(TEMP_MIN_PLAUSIBLE_C),
          max_val(TEMP_MAX_PLAUSIBLE_C),
          max_delta(TEMP_MAX_STEP_DELTA_C),
          last_valid(0.0f),
          has_last_valid(false) {}

    bool is_plausible(float temp_c) const {
        if (temp_c < min_val || temp_c > max_val) {
            return false;
        }
        if (has_last_valid) {
            float diff = temp_c - last_valid;
            if (diff < 0.0f) {
                diff = -diff;
            }
            if (diff > max_delta) {
                return false;
            }
        }
        return true;
    }

    float filter(float temp_c) {
        if (is_plausible(temp_c)) {
            last_valid = temp_c;
            has_last_valid = true;
            return temp_c;
        }
        return has_last_valid ? last_valid : temp_c;
    }

    void reset() {
        last_valid = 0.0f;
        has_last_valid = false;
    }

private:
    float min_val;
    float max_val;
    float max_delta;
    float last_valid;
    bool has_last_valid;
};

template <uint8_t WindowSize = 8>
class TemperatureMovingAverage {
public:
    TemperatureMovingAverage() : index(0), count(0), sum(0.0f) {
        for (uint8_t i = 0; i < WindowSize; ++i) {
            buffer[i] = 0.0f;
        }
    }

    float step(float input) {
        sum -= buffer[index];
        buffer[index] = input;
        sum += input;
        index = (index + 1) % WindowSize;
        if (count < WindowSize) {
            count++;
        }
        return sum / static_cast<float>(count);
    }

    float get_average() const {
        return (count == 0) ? 0.0f : (sum / static_cast<float>(count));
    }

    float get_variance() const {
        if (count < 2) {
            return 0.0f;
        }
        float avg = get_average();
        float var_sum = 0.0f;
        for (uint8_t i = 0; i < count; ++i) {
            float diff = buffer[i] - avg;
            var_sum += diff * diff;
        }
        return var_sum / static_cast<float>(count);
    }

    bool is_stable(float max_variance = 0.04f) const {
        return (count == WindowSize) && (get_variance() <= max_variance);
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

#endif
