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

static constexpr uint16_t STEPPER_STEPS_PER_REV = 200;
static constexpr uint8_t STEPPER_MICROSTEPS = 16;
static constexpr uint8_t STEPPER_TOTAL_COMPARTMENTS = 14;
static constexpr uint32_t STEPPER_MAX_SPEED_STEPS_S = 1600;
static constexpr uint32_t STEPPER_ACCEL_STEPS_S2 = 3200;

static constexpr const char* WIFI_DEFAULT_SSID = "DroidNet";
static constexpr const char* WIFI_DEFAULT_PASS = "AssistiveDroid2026";
static constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 10000;
static constexpr uint32_t WIFI_RECONNECT_INTERVAL_MS = 5000;

static constexpr const char* MQTT_DEFAULT_BROKER = "192.168.4.1";
static constexpr uint16_t MQTT_DEFAULT_PORT = 1883;
static constexpr const char* MQTT_CLIENT_ID = "droid-esp32-vitals";
static constexpr uint16_t MQTT_KEEPALIVE_SEC = 15;
static constexpr uint16_t MQTT_BUFFER_SIZE = 1024;
static constexpr uint32_t MQTT_RECONNECT_INTERVAL_MS = 3000;
static constexpr uint16_t MQTT_OFFLINE_QUEUE_CAPACITY = 500;
static constexpr uint32_t MQTT_PROCESSED_RATE_LIMIT_MS = 500;

static constexpr uint32_t STACK_SIZE_NETWORK = 4096;
static constexpr uint8_t PRIORITY_NETWORK = 2;

#endif

