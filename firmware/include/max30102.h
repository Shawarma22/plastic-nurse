#ifndef MAX30102_H
#define MAX30102_H

#include <stdint.h>
#include <stdbool.h>
#include <Wire.h>
#include "max30102_regs.h"

class MAX30102 {
public:
    MAX30102();
    bool begin(uint32_t i2cSpeed = 400000);
    void reset();
    uint8_t readPartID();
    void setup(
        uint8_t powerLevel = 0x1F,
        uint8_t sampleAverage = MASK_SAMPLE_AVG_4,
        uint8_t ledMode = MASK_MODE_SPO2,
        uint8_t sampleRate = MASK_SAMPLERATE_100HZ,
        uint8_t pulseWidth = MASK_PULSE_WIDTH_411US,
        uint8_t adcRange = MASK_ADC_RGE_4096NA
    );
    void setPulseAmplitudeRed(uint8_t amplitude);
    void setPulseAmplitudeIR(uint8_t amplitude);
    void clearFIFO();
    uint8_t readFIFO(uint32_t* redBuffer, uint32_t* irBuffer, uint8_t maxSamples);
    uint8_t readRegister8(uint8_t address);
    void writeRegister8(uint8_t address, uint8_t data);
    void bitMask(uint8_t reg, uint8_t mask, uint8_t thing);

private:
    uint8_t activeAddress;
};

#endif
