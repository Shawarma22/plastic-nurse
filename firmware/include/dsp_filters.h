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

template <uint8_t CAPACITY = 8>
class HeartRateEstimator {
public:
    HeartRateEstimator(float sampleRateHz = 100.0f)
        : sampleRateHz(sampleRateHz), index(0), count(0), lastBpm(0.0f) {
        for (uint8_t i = 0; i < CAPACITY; ++i) {
            intervals[i] = 0.0f;
        }
    }

    void addInterval(uint16_t sampleCount) {
        float intervalMs = (static_cast<float>(sampleCount) / sampleRateHz) * 1000.0f;
        if (intervalMs < 300.0f || intervalMs > 2000.0f) {
            return;
        }

        intervals[index] = intervalMs;
        index = (index + 1) % CAPACITY;
        if (count < CAPACITY) {
            count++;
        }

        float sum = 0.0f;
        for (uint8_t i = 0; i < count; ++i) {
            sum += intervals[i];
        }
        float avgIntervalMs = sum / static_cast<float>(count);
        lastBpm = 60000.0f / avgIntervalMs;
    }

    float getBPM() const {
        return lastBpm;
    }

    void reset() {
        index = 0;
        count = 0;
        lastBpm = 0.0f;
        for (uint8_t i = 0; i < CAPACITY; ++i) {
            intervals[i] = 0.0f;
        }
    }

private:
    float sampleRateHz;
    float intervals[CAPACITY];
    uint8_t index;
    uint8_t count;
    float lastBpm;
};

class RatioCalculator {
public:
    RatioCalculator() : redAC(0.0f), redDC(1.0f), irAC(0.0f), irDC(1.0f), lastRatio(0.0f) {}

    void update(float redACVal, float redDCVal, float irACVal, float irDCVal) {
        redAC = (redACVal < 0.0f) ? -redACVal : redACVal;
        irAC = (irACVal < 0.0f) ? -irACVal : irACVal;
        redDC = (redDCVal > 1.0f) ? redDCVal : 1.0f;
        irDC = (irDCVal > 1.0f) ? irDCVal : 1.0f;

        float redNorm = redAC / redDC;
        float irNorm = irAC / irDC;

        if (irNorm > 0.0001f) {
            lastRatio = redNorm / irNorm;
        }
    }

    float getRatio() const {
        return lastRatio;
    }

    void reset() {
        redAC = 0.0f;
        redDC = 1.0f;
        irAC = 0.0f;
        irDC = 1.0f;
        lastRatio = 0.0f;
    }

private:
    float redAC;
    float redDC;
    float irAC;
    float irDC;
    float lastRatio;
};

#endif
