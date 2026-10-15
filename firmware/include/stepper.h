#ifndef STEPPER_H
#define STEPPER_H

#include <stdint.h>
#include <stdbool.h>
#include "pinout.h"
#include "config.h"

enum class StepperState : uint8_t {
    Idle = 0,
    Accelerating = 1,
    Running = 2,
    Decelerating = 3,
    Homing = 4,
    ErrorStall = 5
};

enum class StepperDir : uint8_t {
    CW = 0,
    CCW = 1
};

class StepperDriver {
public:
    StepperDriver(
        uint8_t pin_step = PIN_STEPPER_STEP,
        uint8_t pin_dir = PIN_STEPPER_DIR,
        uint8_t pin_en = PIN_STEPPER_ENABLE,
        uint8_t pin_home = PIN_STEPPER_HOME
    );

    bool init();
    void enable();
    void disable();
    bool is_enabled() const;

    void set_direction(StepperDir dir);
    void step_pulse();
    void move_steps(int32_t steps, uint32_t speed_steps_s);
    void stop();
    void emergency_stop();
    bool is_moving() const;

    int32_t get_current_position() const;
    int32_t get_target_position() const;
    void set_current_position(int32_t pos);
    bool is_homed() const;
    bool is_home_switch_active() const;
    StepperState get_state() const;
    void set_acceleration(uint32_t accel);
    uint32_t get_current_speed() const;
    void compute_profile(uint32_t steps, uint32_t target_speed);
    uint32_t next_step_interval_us();

private:
    uint8_t pin_step;
    uint8_t pin_dir;
    uint8_t pin_en;
    uint8_t pin_home;

    StepperState state;
    StepperDir current_dir;
    int32_t current_pos;
    int32_t target_pos;
    uint32_t max_speed;
    uint32_t min_speed;
    uint32_t current_speed;
    uint32_t acceleration;
    uint32_t total_steps;
    uint32_t step_count;
    uint32_t accel_steps;
    uint32_t decel_start_step;
    uint32_t step_interval_us;
    bool enabled;
    bool homed;
};

#endif
