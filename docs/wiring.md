# Hardware Wiring & Pinout Reference

## Critical Pin Verification Notice

Do not power or connect actuators until continuity and GPIO assignments are physically verified with a multimeter on the target board. Historical codebases contained conflicting pin mappings (`4/17/27/22` vs `17/27/18/22/23/13`).

## Motor Controller (L298N)

| Function | Default BCM Pin | Physical Header Pin | Config Key |
|---|---|---|---|
| Motor Left Forward (IN1) | 17 | Pin 11 | `PIN_MOTOR_L_FWD` |
| Motor Left Backward (IN2) | 27 | Pin 13 | `PIN_MOTOR_L_BWD` |
| Motor Left PWM (ENA) | 18 | Pin 12 | `PIN_MOTOR_L_PWM` |
| Motor Right Forward (IN3) | 22 | Pin 15 | `PIN_MOTOR_R_FWD` |
| Motor Right Backward (IN4) | 23 | Pin 16 | `PIN_MOTOR_R_BWD` |
| Motor Right PWM (ENB) | 13 | Pin 33 | `PIN_MOTOR_R_PWM` |

## Door Actuator

| Function | Default BCM Pin | Physical Header Pin | Config Key |
|---|---|---|---|
| Door Motor Open (IN1) | 24 | Pin 18 | `PIN_DOOR_OPEN` |
| Door Motor Close (IN2) | 25 | Pin 22 | `PIN_DOOR_CLOSE` |
| Door Limit Switch Open | 5 | Pin 29 | `PIN_DOOR_LIMIT_OPEN` |
| Door Limit Switch Closed | 6 | Pin 31 | `PIN_DOOR_LIMIT_CLOSED` |

## Emergency Stop & Sensors

| Function | Default BCM Pin | Physical Header Pin | Config Key |
|---|---|---|---|
| Hardware E-Stop Button | 26 | Pin 37 | `PIN_ESTOP` |
| HC-SR04 Ultrasonic Trigger | 16 | Pin 36 | `PIN_ULTRASONIC_TRIG` |
| HC-SR04 Ultrasonic Echo | 12 | Pin 32 | `PIN_ULTRASONIC_ECHO` |

## I2C Bus

| Function | BCM Pin | Physical Header Pin |
|---|---|---|
| SDA | GPIO 2 | Pin 3 |
| SCL | GPIO 3 | Pin 5 |
