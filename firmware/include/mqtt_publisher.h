#ifndef MQTT_PUBLISHER_H
#define MQTT_PUBLISHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "config.h"
#include "mqtt_topics.h"
#include "sensor_types.h"
#include <WiFiClient.h>
#include <PubSubClient.h>

enum class MqttState : uint8_t {
    Disconnected = 0,
    Connecting = 1,
    Connected = 2,
    Failed = 3
};

class MqttPublisher {
public:
    MqttPublisher(
        const char* broker = MQTT_DEFAULT_BROKER,
        uint16_t port = MQTT_DEFAULT_PORT,
        const char* client_id = MQTT_CLIENT_ID
    );

    bool init();
    bool connect();
    void disconnect();
    bool update();
    bool is_connected();
    MqttState get_state() const;

    bool publish_processed(const SensorPacket& packet);
    bool publish_raw(const uint8_t* payload, size_t length);
    bool publish_event(const char* event_type, const char* details);
    bool publish_status(const char* status);

    void set_broker(const char* broker, uint16_t port);
    uint32_t get_published_count() const;
    uint32_t get_dropped_count() const;

private:
    const char* broker_host;
    uint16_t broker_port;
    const char* client_id_str;
    MqttState state;
    uint32_t last_reconnect_attempt_ms;
    uint32_t published_count;
    uint32_t dropped_count;
    WiFiClient wifi_client;
    PubSubClient mqtt_client;
    char buffer[MQTT_BUFFER_SIZE];
};

#endif
