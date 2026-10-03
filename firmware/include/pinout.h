#ifndef PINOUT_H
#define PINOUT_H

#include <stdint.h>

static constexpr uint8_t PIN_I2C_SDA = 21;
static constexpr uint8_t PIN_I2C_SCL = 22;

static constexpr uint8_t PIN_MAX30102_INT = 19;

static constexpr uint8_t PIN_AD8232_OUT = 34;
static constexpr uint8_t PIN_AD8232_LO_PLUS = 32;
static constexpr uint8_t PIN_AD8232_LO_MINUS = 33;
static constexpr uint8_t PIN_AD8232_SDN = 25;

static constexpr uint8_t PIN_LED_STATUS = 2;
static constexpr uint8_t PIN_LED_WIFI = 4;
static constexpr uint8_t PIN_LED_SENSOR = 16;

#endif
