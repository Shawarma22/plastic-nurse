#ifndef MQTT_TOPICS_H
#define MQTT_TOPICS_H

#include <stdint.h>

static constexpr const char* TOPIC_VITALS_PROCESSED = "droid/vitals/processed";
static constexpr const char* TOPIC_VITALS_RAW = "droid/vitals/raw";
static constexpr const char* TOPIC_VITALS_EVENTS = "droid/vitals/events";
static constexpr const char* TOPIC_CMD_DISPENSE = "droid/cmd/dispense";
static constexpr const char* TOPIC_STATUS_LWT = "droid/status/lwt";

static constexpr const char* LWT_PAYLOAD_ONLINE = "online";
static constexpr const char* LWT_PAYLOAD_OFFLINE = "offline";

static constexpr uint8_t MQTT_QOS_PROCESSED = 1;
static constexpr uint8_t MQTT_QOS_RAW = 0;
static constexpr uint8_t MQTT_QOS_EVENTS = 1;
static constexpr uint8_t MQTT_QOS_LWT = 1;

#endif
