#ifndef MQTT_PUBLISHER_H
#define MQTT_PUBLISHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "config.h"
#include "mqtt_topics.h"
#include "sensor_types.h"
#include "telemetry_ring_buffer.h"
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
    bool subscribe_commands();
    static void handle_incoming_message(char* topic, uint8_t* payload, unsigned int length);
    bool queue_offline_packet(const SensorPacket& packet);
    size_t flush_offline_queue(size_t max_packets = 50);
    size_t get_queued_packet_count() const;
    TelemetryRingBuffer<MQTT_OFFLINE_QUEUE_CAPACITY>& get_offline_queue();
    void set_rate_limit_interval(uint32_t interval_ms);
    uint32_t get_rate_limit_interval() const;
    bool can_publish_now() const;

private:
    const char* broker_host;
    uint16_t broker_port;
    const char* client_id_str;
    MqttState state;
    uint32_t last_reconnect_attempt_ms;
    uint32_t published_count;
    uint32_t dropped_count;
    uint32_t min_publish_interval_ms;
    uint32_t last_publish_time_ms;
    WiFiClient wifi_client;
    PubSubClient mqtt_client;
    TelemetryRingBuffer<MQTT_OFFLINE_QUEUE_CAPACITY> offline_queue;
    char buffer[MQTT_BUFFER_SIZE];
};

#endif
