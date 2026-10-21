#include "mqtt_publisher.h"
#include "packet_serializer.h"
#include "tasks.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <stdio.h>

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
    mqtt_client.setCallback(handle_incoming_message);
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
        subscribe_commands();
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
        if (!offline_queue.is_empty()) {
            flush_offline_queue(10);
        }
        return true;
    }

    uint32_t now = millis();
    if (now - last_reconnect_attempt_ms >= MQTT_RECONNECT_INTERVAL_MS) {
        last_reconnect_attempt_ms = now;
        bool ok = connect();
        if (ok) {
            flush_offline_queue(25);
        }
        return ok;
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
        queue_offline_packet(packet);
        dropped_count++;
        return false;
    }
    size_t len = serializeSensorPacket(packet, buffer, sizeof(buffer));
    if (len == 0) {
        dropped_count++;
        return false;
    }
    bool ok = mqtt_client.publish(TOPIC_VITALS_PROCESSED, buffer);
    if (ok) {
        published_count++;
    } else {
        queue_offline_packet(packet);
        dropped_count++;
    }
    return ok;
}

bool MqttPublisher::publish_raw(const uint8_t* payload, size_t length) {
    if (!mqtt_client.connected() || payload == nullptr || length == 0) {
        dropped_count++;
        return false;
    }
    bool ok = mqtt_client.publish(TOPIC_VITALS_RAW, payload, length);
    if (ok) {
        published_count++;
    } else {
        dropped_count++;
    }
    return ok;
}

bool MqttPublisher::publish_event(const char* event_type, const char* details) {
    if (!mqtt_client.connected() || event_type == nullptr) {
        dropped_count++;
        return false;
    }
    snprintf(buffer, sizeof(buffer), "{\"event\":\"%s\",\"details\":\"%s\",\"ts\":%lu}",
             event_type, details ? details : "", static_cast<unsigned long>(millis()));
    bool ok = mqtt_client.publish(TOPIC_VITALS_EVENTS, buffer);
    if (ok) {
        published_count++;
    } else {
        dropped_count++;
    }
    return ok;
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

bool MqttPublisher::queue_offline_packet(const SensorPacket& packet) {
    return offline_queue.push(packet);
}

size_t MqttPublisher::flush_offline_queue(size_t max_packets) {
    if (!mqtt_client.connected() || offline_queue.is_empty()) {
        return 0;
    }

    size_t flushed = 0;
    SensorPacket packet{};

    while (flushed < max_packets && offline_queue.pop(packet)) {
        size_t len = serializeSensorPacket(packet, buffer, sizeof(buffer));
        if (len > 0 && mqtt_client.publish(TOPIC_VITALS_PROCESSED, buffer)) {
            published_count++;
            flushed++;
        } else {
            offline_queue.push(packet);
            break;
        }
    }

    return flushed;
}

size_t MqttPublisher::get_queued_packet_count() const {
    return offline_queue.size();
}

TelemetryRingBuffer<MQTT_OFFLINE_QUEUE_CAPACITY>& MqttPublisher::get_offline_queue() {
    return offline_queue;
}

bool MqttPublisher::subscribe_commands() {
    if (!mqtt_client.connected()) {
        return false;
    }
    return mqtt_client.subscribe(TOPIC_CMD_DISPENSE, 1);
}

void MqttPublisher::handle_incoming_message(char* topic, uint8_t* payload, unsigned int length) {
    if (topic == nullptr || payload == nullptr || length == 0) {
        return;
    }

    if (strcmp(topic, TOPIC_CMD_DISPENSE) == 0 && xQueueDispenseCmd != nullptr) {
        StaticJsonDocument<256> doc;
        DeserializationError err = deserializeJson(doc, payload, length);
        if (err) {
            return;
        }

        const char* cmd = doc["cmd"] | "";
        DispenseCommand dispenseCmd{};

        if (strcmp(cmd, "dispense") == 0 || strcmp(cmd, "move") == 0) {
            dispenseCmd.type = DispenseCmdType::MoveToCompartment;
            dispenseCmd.compartment = doc["compartment"] | 0;
            xQueueSend(xQueueDispenseCmd, &dispenseCmd, 0);
        } else if (strcmp(cmd, "home") == 0) {
            dispenseCmd.type = DispenseCmdType::Home;
            dispenseCmd.compartment = 0;
            xQueueSend(xQueueDispenseCmd, &dispenseCmd, 0);
        } else if (strcmp(cmd, "stop") == 0 || strcmp(cmd, "estop") == 0) {
            dispenseCmd.type = DispenseCmdType::EmergencyStop;
            dispenseCmd.compartment = 0;
            xQueueSend(xQueueDispenseCmd, &dispenseCmd, 0);
        } else if (strcmp(cmd, "clear") == 0 || strcmp(cmd, "clear_stall") == 0) {
            dispenseCmd.type = DispenseCmdType::ClearStall;
            dispenseCmd.compartment = 0;
            xQueueSend(xQueueDispenseCmd, &dispenseCmd, 0);
        }
    }
}

