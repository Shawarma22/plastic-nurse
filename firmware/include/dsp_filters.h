#ifndef DSP_FILTERS_H
#define DSP_FILTERS_H

#include <stdint.h>

class DCRemovalFilter {
public:
    DCRemovalFilter(float alpha = 0.95f);
    float step(float input);
    float getDC() const;
    void reset();

private:
    float alpha;
    float prevInput;
    float prevOutput;
    float dcEstimate;
};

template <uint8_t N = 5>
class MovingAverageFilter {
public:
    MovingAverageFilter() : index(0), count(0), sum(0.0f) {
        for (uint8_t i = 0; i < N; ++i) {
            buffer[i] = 0.0f;
        }
    }

    float step(float input) {
        sum -= buffer[index];
        buffer[index] = input;
        sum += input;
        index = (index + 1) % N;
        if (count < N) {
            count++;
        }
        return sum / static_cast<float>(count);
    }

    float getAverage() const {
        return (count == 0) ? 0.0f : (sum / static_cast<float>(count));
    }

    void reset() {
        index = 0;
        count = 0;
        sum = 0.0f;
        for (uint8_t i = 0; i < N; ++i) {
            buffer[i] = 0.0f;
        }
    }

private:
    float buffer[N];
    uint8_t index;
    uint8_t count;
    float sum;
};

#endif
