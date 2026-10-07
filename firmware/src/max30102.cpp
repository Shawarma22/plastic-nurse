#include "max30102.h"
#include <Arduino.h>

MAX30102::MAX30102() : activeAddress(MAX30102_I2C_ADDR) {}

bool MAX30102::begin(uint32_t i2cSpeed) {
    Wire.setClock(i2cSpeed);
    if (readPartID() != MAX30102_EXPECTED_PART_ID) {
        return false;
    }
    reset();
    return true;
}

void MAX30102::reset() {
    bitMask(REG_MODE_CONFIG, static_cast<uint8_t>(~MASK_MODE_RESET), MASK_MODE_RESET);
    unsigned long startTime = millis();
    while (millis() - startTime < 100) {
        uint8_t response = readRegister8(REG_MODE_CONFIG);
        if ((response & MASK_MODE_RESET) == 0) {
            break;
        }
        delay(1);
    }
}

uint8_t MAX30102::readPartID() {
    return readRegister8(REG_PART_ID);
}

void MAX30102::setup(
    uint8_t powerLevel,
    uint8_t sampleAverage,
    uint8_t ledMode,
    uint8_t sampleRate,
    uint8_t pulseWidth,
    uint8_t adcRange
) {
    writeRegister8(REG_FIFO_CONFIG, sampleAverage | 0x10);
    writeRegister8(REG_MODE_CONFIG, ledMode);
    writeRegister8(REG_SPO2_CONFIG, adcRange | sampleRate | pulseWidth);
    setPulseAmplitudeRed(powerLevel);
    setPulseAmplitudeIR(powerLevel);
    clearFIFO();
}

void MAX30102::clearFIFO() {
    writeRegister8(REG_FIFO_WR_PTR, 0);
    writeRegister8(REG_OVF_COUNTER, 0);
    writeRegister8(REG_FIFO_RD_PTR, 0);
}

void MAX30102::setPulseAmplitudeRed(uint8_t amplitude) {
    writeRegister8(REG_LED1_PA, amplitude);
}

void MAX30102::setPulseAmplitudeIR(uint8_t amplitude) {
    writeRegister8(REG_LED2_PA, amplitude);
}

void MAX30102::setPulseAmplitudeProximity(uint8_t amplitude) {
    writeRegister8(REG_MULTI_LED_CTRL1, amplitude);
}

uint8_t MAX30102::readRegister8(uint8_t address) {
    Wire.beginTransmission(activeAddress);
    Wire.write(address);
    Wire.endTransmission(false);
    Wire.requestFrom(activeAddress, static_cast<uint8_t>(1));
    if (Wire.available()) {
        return Wire.read();
    }
    return 0;
}

uint8_t MAX30102::readRegisterBytes(uint8_t address, uint8_t* buffer, uint8_t length) {
    Wire.beginTransmission(activeAddress);
    Wire.write(address);
    Wire.endTransmission(false);
    uint8_t count = Wire.requestFrom(activeAddress, length);
    for (uint8_t i = 0; i < count; ++i) {
        if (Wire.available()) {
            buffer[i] = Wire.read();
        }
    }
    return count;
}

bool MAX30102::writeRegister8(uint8_t address, uint8_t data) {
    Wire.beginTransmission(activeAddress);
    Wire.write(address);
    Wire.write(data);
    if (Wire.endTransmission() != 0) {
        return false;
    }
    return true;
}

bool MAX30102::bitMask(uint8_t reg, uint8_t mask, uint8_t thing) {
    uint8_t original = readRegister8(reg);
    original &= mask;
    return writeRegister8(reg, original | thing);
}
