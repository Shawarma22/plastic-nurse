#include "status_led.h"
#include <Arduino.h>

void initStatusLeds() {
    pinMode(static_cast<uint8_t>(LedId::Status), OUTPUT);
    pinMode(static_cast<uint8_t>(LedId::Wifi), OUTPUT);
    pinMode(static_cast<uint8_t>(LedId::Sensor), OUTPUT);

    digitalWrite(static_cast<uint8_t>(LedId::Status), LOW);
    digitalWrite(static_cast<uint8_t>(LedId::Wifi), LOW);
    digitalWrite(static_cast<uint8_t>(LedId::Sensor), LOW);
}

void setLedState(LedId led, bool state) {
    digitalWrite(static_cast<uint8_t>(led), state ? HIGH : LOW);
}

void toggleLed(LedId led) {
    uint8_t pin = static_cast<uint8_t>(led);
    digitalWrite(pin, !digitalRead(pin));
}

bool getLedState(LedId led) {
    return digitalRead(static_cast<uint8_t>(led)) == HIGH;
}
