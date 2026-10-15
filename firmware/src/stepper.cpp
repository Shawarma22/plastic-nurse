#include "stepper.h"
#include <Arduino.h>

StepperDriver::StepperDriver(
    uint8_t pin_step,
    uint8_t pin_dir,
    uint8_t pin_en,
    uint8_t pin_home
) : pin_step(pin_step),
    pin_dir(pin_dir),
    pin_en(pin_en),
    pin_home(pin_home),
    state(StepperState::Idle),
    current_dir(StepperDir::CW),
    current_pos(0),
    target_pos(0),
    max_speed(STEPPER_MAX_SPEED_STEPS_S),
    enabled(false),
    homed(false) {}

bool StepperDriver::init() {
    pinMode(pin_step, OUTPUT);
    pinMode(pin_dir, OUTPUT);
    pinMode(pin_en, OUTPUT);
    pinMode(pin_home, INPUT_PULLUP);

    digitalWrite(pin_step, LOW);
    digitalWrite(pin_dir, LOW);
    disable();

    state = StepperState::Idle;
    current_pos = 0;
    target_pos = 0;
    homed = false;
    return true;
}

void StepperDriver::enable() {
    digitalWrite(pin_en, LOW);
    enabled = true;
}

void StepperDriver::disable() {
    digitalWrite(pin_en, HIGH);
    enabled = false;
    state = StepperState::Idle;
}

bool StepperDriver::is_enabled() const {
    return enabled;
}

void StepperDriver::set_direction(StepperDir dir) {
    current_dir = dir;
    digitalWrite(pin_dir, (dir == StepperDir::CW) ? HIGH : LOW);
}

void StepperDriver::step_pulse() {
    digitalWrite(pin_step, HIGH);
    delayMicroseconds(2);
    digitalWrite(pin_step, LOW);

    if (current_dir == StepperDir::CW) {
        current_pos++;
    } else {
        current_pos--;
    }
}

int32_t StepperDriver::get_current_position() const {
    return current_pos;
}

int32_t StepperDriver::get_target_position() const {
    return target_pos;
}

void StepperDriver::set_current_position(int32_t pos) {
    current_pos = pos;
}

bool StepperDriver::is_homed() const {
    return homed;
}

bool StepperDriver::is_home_switch_active() const {
    return (digitalRead(pin_home) == LOW);
}

StepperState StepperDriver::get_state() const {
    return state;
}
