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
