#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

static constexpr uint32_t SERIAL_BAUD = 115200;
static constexpr uint32_t I2C_FREQ_HZ = 400000;

static constexpr uint16_t MAX30102_SAMPLE_RATE_HZ = 100;
static constexpr uint16_t AD8232_SAMPLE_RATE_HZ = 250;

static constexpr uint32_t STACK_SIZE_HEARTBEAT = 2048;
static constexpr uint32_t STACK_SIZE_SENSORS = 4096;
static constexpr uint32_t STACK_SIZE_TELEMETRY = 4096;

static constexpr uint8_t PRIORITY_HEARTBEAT = 1;
static constexpr uint8_t PRIORITY_TELEMETRY = 2;
static constexpr uint8_t PRIORITY_SENSORS = 3;

static constexpr uint8_t SENSOR_QUEUE_DEPTH = 32;
static constexpr uint32_t TELEMETRY_INTERVAL_MS = 500;

#endif
