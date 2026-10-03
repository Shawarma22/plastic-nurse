#ifndef STATUS_LED_H
#define STATUS_LED_H

#include <stdint.h>
#include <stdbool.h>
#include "pinout.h"

enum class LedId : uint8_t {
    Status = PIN_LED_STATUS,
    Wifi = PIN_LED_WIFI,
    Sensor = PIN_LED_SENSOR
};

void initStatusLeds();
void setLedState(LedId led, bool state);
void toggleLed(LedId led);
bool getLedState(LedId led);

#endif
