#include "mqtt_publisher.h"
#include <Arduino.h>

MqttPublisher::MqttPublisher(const char* broker, uint16_t port, const char* client_id)
    : broker_host(broker),
      broker_port(port),
      client_id_str(client_id),
      state(MqttState::Disconnected),
      last_reconnect_attempt_ms(0),
      published_count(0),
      dropped_count(0),
      mqtt_client(wifi_client) {
    buffer[0] = '\0';
}

bool MqttPublisher::init() {
    mqtt_client.setServer(broker_host, broker_port);
    mqtt_client.setBufferSize(MQTT_BUFFER_SIZE);
    mqtt_client.setKeepAlive(MQTT_KEEPALIVE_SEC);
    state = MqttState::Disconnected;
    return true;
}

bool MqttPublisher::connect() {
    if (mqtt_client.connected()) {
        state = MqttState::Connected;
        return true;
    }

    state = MqttState::Connecting;
    bool success = mqtt_client.connect(
        client_id_str,
        TOPIC_STATUS_LWT,
        MQTT_QOS_LWT,
        true,
        LWT_PAYLOAD_OFFLINE
    );

    if (success) {
        state = MqttState::Connected;
        publish_status(LWT_PAYLOAD_ONLINE);
        return true;
    }

    state = MqttState::Failed;
    last_reconnect_attempt_ms = millis();
    return false;
}

void MqttPublisher::disconnect() {
    if (mqtt_client.connected()) {
        publish_status(LWT_PAYLOAD_OFFLINE);
        mqtt_client.disconnect();
    }
    state = MqttState::Disconnected;
}

bool MqttPublisher::update() {
    if (mqtt_client.connected()) {
        state = MqttState::Connected;
        mqtt_client.loop();
        return true;
    }

    uint32_t now = millis();
    if (now - last_reconnect_attempt_ms >= MQTT_RECONNECT_INTERVAL_MS) {
        last_reconnect_attempt_ms = now;
        return connect();
    }

    return false;
}

bool MqttPublisher::is_connected() {
    return mqtt_client.connected();
}

MqttState MqttPublisher::get_state() const {
    return state;
}

bool MqttPublisher::publish_status(const char* status) {
    if (!mqtt_client.connected()) {
        return false;
    }
    return mqtt_client.publish(TOPIC_STATUS_LWT, status, true);
}

bool MqttPublisher::publish_processed(const SensorPacket& packet) {
    if (!mqtt_client.connected()) {
        dropped_count++;
        return false;
    }
    published_count++;
    return true;
}

bool MqttPublisher::publish_raw(const uint8_t* payload, size_t length) {
    if (!mqtt_client.connected()) {
        dropped_count++;
        return false;
    }
    published_count++;
    return true;
}

bool MqttPublisher::publish_event(const char* event_type, const char* details) {
    if (!mqtt_client.connected()) {
        dropped_count++;
        return false;
    }
    published_count++;
    return true;
}

void MqttPublisher::set_broker(const char* broker, uint16_t port) {
    broker_host = broker;
    broker_port = port;
    mqtt_client.setServer(broker_host, broker_port);
    if (mqtt_client.connected()) {
        disconnect();
    }
}

uint32_t MqttPublisher::get_published_count() const {
    return published_count;
}

uint32_t MqttPublisher::get_dropped_count() const {
    return dropped_count;
}
