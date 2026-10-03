#include "i2c_bus.h"

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
