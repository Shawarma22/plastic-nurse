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
    min_speed(200),
    current_speed(200),
    acceleration(STEPPER_ACCEL_STEPS_S2),
    total_steps(0),
    step_count(0),
    accel_steps(0),
    decel_start_step(0),
    step_interval_us(5000),
    last_step_time_us(0),
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

void StepperDriver::set_acceleration(uint32_t accel) {
    if (accel > 0) {
        acceleration = accel;
    }
}

uint32_t StepperDriver::get_current_speed() const {
    return current_speed;
}

void StepperDriver::compute_profile(uint32_t steps, uint32_t target_speed) {
    total_steps = steps;
    step_count = 0;
    max_speed = target_speed;
    current_speed = min_speed;
    step_interval_us = 1000000UL / current_speed;

    uint32_t needed_accel_steps = (max_speed * max_speed - min_speed * min_speed) / (2 * acceleration);
    if (needed_accel_steps == 0) {
        needed_accel_steps = 1;
    }

    if (needed_accel_steps * 2 > total_steps) {
        accel_steps = total_steps / 2;
        decel_start_step = total_steps - accel_steps;
    } else {
        accel_steps = needed_accel_steps;
        decel_start_step = total_steps - needed_accel_steps;
    }

    state = (total_steps > 0) ? StepperState::Accelerating : StepperState::Idle;
}

uint32_t StepperDriver::next_step_interval_us() {
    if (step_count < accel_steps) {
        state = StepperState::Accelerating;
        float progress = static_cast<float>(step_count) / static_cast<float>(accel_steps > 0 ? accel_steps : 1);
        current_speed = min_speed + static_cast<uint32_t>((max_speed - min_speed) * progress);
    } else if (step_count >= decel_start_step) {
        state = StepperState::Decelerating;
        uint32_t decel_step = step_count - decel_start_step;
        uint32_t decel_total = total_steps - decel_start_step;
        float progress = static_cast<float>(decel_step) / static_cast<float>(decel_total > 0 ? decel_total : 1);
        current_speed = max_speed - static_cast<uint32_t>((max_speed - min_speed) * progress);
    } else {
        state = StepperState::Running;
        current_speed = max_speed;
    }

    if (current_speed < min_speed) {
        current_speed = min_speed;
    }

    step_interval_us = 1000000UL / current_speed;
    step_count++;
    return step_interval_us;
}

void StepperDriver::move_steps(int32_t steps, uint32_t speed_steps_s) {
    if (steps == 0) {
        return;
    }
    enable();
    uint32_t abs_steps = (steps < 0) ? -steps : steps;
    set_direction((steps > 0) ? StepperDir::CW : StepperDir::CCW);
    target_pos = current_pos + steps;
    compute_profile(abs_steps, speed_steps_s > 0 ? speed_steps_s : max_speed);
    last_step_time_us = micros();
}

void StepperDriver::move_to(int32_t absolute_position, uint32_t speed_steps_s) {
    int32_t delta = absolute_position - current_pos;
    move_steps(delta, speed_steps_s);
}

bool StepperDriver::update() {
    if (!is_moving()) {
        return false;
    }

    uint32_t now = micros();
    if (now - last_step_time_us < step_interval_us) {
        return true;
    }

    last_step_time_us = now;
    step_pulse();

    if (step_count < total_steps) {
        next_step_interval_us();
    } else {
        state = StepperState::Idle;
    }

    return is_moving();
}

void StepperDriver::stop() {
    state = StepperState::Idle;
    total_steps = 0;
    step_count = 0;
    target_pos = current_pos;
}

void StepperDriver::emergency_stop() {
    state = StepperState::ErrorStall;
    total_steps = 0;
    step_count = 0;
    target_pos = current_pos;
    disable();
}

bool StepperDriver::is_moving() const {
    return (state == StepperState::Accelerating ||
            state == StepperState::Running ||
            state == StepperState::Decelerating ||
            state == StepperState::Homing);
}

