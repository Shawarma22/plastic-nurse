#include "i2c_bus.h"
#include <Arduino.h>

bool initI2CBus() {
    return Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQ_HZ);
}

uint8_t scanI2CBus(uint8_t* foundAddresses, uint8_t maxFound) {
    uint8_t count = 0;
    for (uint8_t address = 1; address < 127; ++address) {
        Wire.beginTransmission(address);
        uint8_t error = Wire.endTransmission();
        if (error == 0) {
            if (foundAddresses != nullptr && count < maxFound) {
                foundAddresses[count] = address;
            }
            count++;
        }
    }
    return count;
}

bool isDeviceConnected(uint8_t address) {
    Wire.beginTransmission(address);
    return (Wire.endTransmission() == 0);
}

bool recoverI2CBus() {
    Wire.end();
    pinMode(PIN_I2C_SDA, INPUT_PULLUP);
    pinMode(PIN_I2C_SCL, OUTPUT);
    digitalWrite(PIN_I2C_SCL, HIGH);
    delayMicroseconds(10);

    for (int i = 0; i < 9; ++i) {
        if (digitalRead(PIN_I2C_SDA) == HIGH) {
            break;
        }
        digitalWrite(PIN_I2C_SCL, LOW);
        delayMicroseconds(10);
        digitalWrite(PIN_I2C_SCL, HIGH);
        delayMicroseconds(10);
    }

    pinMode(PIN_I2C_SDA, OUTPUT);
    digitalWrite(PIN_I2C_SDA, LOW);
    delayMicroseconds(10);
    digitalWrite(PIN_I2C_SCL, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_I2C_SDA, HIGH);
    delayMicroseconds(10);

    return initI2CBus();
}
