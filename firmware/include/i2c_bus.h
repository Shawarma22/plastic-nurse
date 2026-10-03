#ifndef I2C_BUS_H
#define I2C_BUS_H

#include <stdint.h>
#include <Wire.h>
#include "pinout.h"
#include "config.h"

bool initI2CBus();
uint8_t scanI2CBus(uint8_t* foundAddresses, uint8_t maxFound);
bool isDeviceConnected(uint8_t address);
bool recoverI2CBus();

#endif
