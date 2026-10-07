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

class PeakDetector {
public:
    PeakDetector(uint16_t minRefractorySamples = 30, float threshold = 20.0f)
        : minRefractory(minRefractorySamples),
          threshold(threshold),
          lastSample(0.0f),
          samplesSincePeak(0),
          isRising(false),
          peakValue(0.0f),
          valleyValue(0.0f) {}

    bool step(float sample) {
        samplesSincePeak++;
        bool peakDetected = false;

        if (sample > lastSample) {
            isRising = true;
        } else if (isRising && sample < lastSample) {
            isRising = false;
            if (lastSample > threshold && samplesSincePeak >= minRefractory) {
                peakDetected = true;
                peakValue = lastSample;
                samplesSincePeak = 0;
            }
        }

        if (sample < valleyValue) {
            valleyValue = sample;
        } else if (peakDetected) {
            valleyValue = sample;
        }

        lastSample = sample;
        return peakDetected;
    }

    float getPeak() const {
        return peakValue;
    }

    float getValley() const {
        return valleyValue;
    }

    uint16_t getSamplesSincePeak() const {
        return samplesSincePeak;
    }

    void reset() {
        lastSample = 0.0f;
        samplesSincePeak = 0;
        isRising = false;
        peakValue = 0.0f;
        valleyValue = 0.0f;
    }

private:
    uint16_t minRefractory;
    float threshold;
    float lastSample;
    uint16_t samplesSincePeak;
    bool isRising;
    float peakValue;
    float valleyValue;
};

#endif
