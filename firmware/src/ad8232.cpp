#include "ad8232.h"
#include <Arduino.h>

AD8232Driver::AD8232Driver(
    uint8_t pin_out,
    uint8_t pin_lo_plus,
    uint8_t pin_lo_minus,
    uint8_t pin_sdn
) : pin_out(pin_out),
    pin_lo_plus(pin_lo_plus),
    pin_lo_minus(pin_lo_minus),
    pin_sdn(pin_sdn),
    initialized(false),
    leads_attached(false),
    last_raw_sample(0) {}

bool AD8232Driver::init() {
    pinMode(pin_out, INPUT);
    pinMode(pin_lo_plus, INPUT);
    pinMode(pin_lo_minus, INPUT);

    if (pin_sdn != 255) {
        pinMode(pin_sdn, OUTPUT);
        digitalWrite(pin_sdn, HIGH);
    }

    analogReadResolution(12);
    analogSetPinAttenuation(pin_out, ADC_11db);

    initialized = true;
    leads_attached = false;
    return true;
}
