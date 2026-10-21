#include "tasks.h"
#include "network_manager.h"
#include "mqtt_publisher.h"
#include "sensor_types.h"
#include <Arduino.h>

static NetworkManager networkManager;
static MqttPublisher mqttPublisher;

NetworkManager& getNetworkManager() {
    return networkManager;
}

MqttPublisher& getMqttPublisher() {
    return mqttPublisher;
}

void taskTelemetry(void* pvParameters) {
    networkManager.init();
    networkManager.connect();
    mqttPublisher.init();

    SensorPacket packet{};
    char eventBuffer[32];
    const TickType_t delayTicks = pdMS_TO_TICKS(10);

    for (;;) {
        networkManager.update();

        if (networkManager.is_connected()) {
            mqttPublisher.update();

            while (xQueueSensorData != nullptr && xQueueReceive(xQueueSensorData, &packet, 0) == pdTRUE) {
                mqttPublisher.publish_processed(packet);
            }

            if (xQueueEvents != nullptr && xQueueReceive(xQueueEvents, eventBuffer, 0) == pdTRUE) {
                eventBuffer[sizeof(eventBuffer) - 1] = '\0';
                mqttPublisher.publish_event("SYSTEM", eventBuffer);
            }
        } else {
            while (xQueueSensorData != nullptr && xQueueReceive(xQueueSensorData, &packet, 0) == pdTRUE) {
                mqttPublisher.queue_offline_packet(packet);
            }
        }

        vTaskDelay(delayTicks);
    }
}
