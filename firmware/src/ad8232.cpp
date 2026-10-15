#include "ad8232.h"
#include <Arduino.h>

volatile bool AD8232Driver::s_leads_changed = false;
void (*AD8232Driver::s_user_callback)() = nullptr;

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

uint16_t AD8232Driver::read_raw() {
    if (!initialized) {
        return 0;
    }
    last_raw_sample = static_cast<uint16_t>(analogRead(pin_out));
    return last_raw_sample;
}

bool AD8232Driver::are_leads_attached() {
    if (!initialized) {
        return false;
    }
    bool lo_plus = (digitalRead(pin_lo_plus) == HIGH);
    bool lo_minus = (digitalRead(pin_lo_minus) == HIGH);
    leads_attached = (!lo_plus && !lo_minus);
    return leads_attached;
}

bool AD8232Driver::is_lo_plus_active() const {
    return (digitalRead(pin_lo_plus) == HIGH);
}

bool AD8232Driver::is_lo_minus_active() const {
    return (digitalRead(pin_lo_minus) == HIGH);
}

uint8_t AD8232Driver::get_leads_status() const {
    uint8_t status = 0;
    if (digitalRead(pin_lo_plus) == HIGH) {
        status |= 0x01;
    }
    if (digitalRead(pin_lo_minus) == HIGH) {
        status |= 0x02;
    }
    return status;
}

bool AD8232Driver::is_connected() const {
    return initialized;
}

uint16_t AD8232Driver::get_sample_rate() const {
    return AD8232_DEFAULT_SAMPLE_RATE;
}

void AD8232Driver::shutdown() {
    if (pin_sdn != 255) {
        digitalWrite(pin_sdn, LOW);
    }
}

void AD8232Driver::resume() {
    if (pin_sdn != 255) {
        digitalWrite(pin_sdn, HIGH);
    }
}

void AD8232Driver::reset() {
    last_raw_sample = 0;
    leads_attached = false;
}

void IRAM_ATTR AD8232Driver::isr_lo_plus() {
    s_leads_changed = true;
    if (s_user_callback) {
        s_user_callback();
    }
}

void IRAM_ATTR AD8232Driver::isr_lo_minus() {
    s_leads_changed = true;
    if (s_user_callback) {
        s_user_callback();
    }
}

bool AD8232Driver::enable_interrupts(void (*callback)()) {
    s_user_callback = callback;
    s_leads_changed = false;
    attachInterrupt(digitalPinToInterrupt(pin_lo_plus), isr_lo_plus, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pin_lo_minus), isr_lo_minus, CHANGE);
    return true;
}

void AD8232Driver::disable_interrupts() {
    detachInterrupt(digitalPinToInterrupt(pin_lo_plus));
    detachInterrupt(digitalPinToInterrupt(pin_lo_minus));
    s_user_callback = nullptr;
}

bool AD8232Driver::has_leads_changed() {
    return s_leads_changed;
}

void AD8232Driver::clear_leads_changed() {
    s_leads_changed = false;
}


