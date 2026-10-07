#include "dsp_filters.h"

DCRemovalFilter::DCRemovalFilter(float alpha)
    : alpha(alpha), prevInput(0.0f), prevOutput(0.0f), dcEstimate(0.0f) {}

float DCRemovalFilter::step(float input) {
    float output = input - prevInput + alpha * prevOutput;
    prevInput = input;
    prevOutput = output;
    dcEstimate = input - output;
    return output;
}

float DCRemovalFilter::getDC() const {
    return dcEstimate;
}

void DCRemovalFilter::reset() {
    prevInput = 0.0f;
    prevOutput = 0.0f;
    dcEstimate = 0.0f;
}
