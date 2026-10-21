#ifndef TASKS_H
#define TASKS_H

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include "config.h"
#include "sensor_types.h"

enum class DispenseCmdType : uint8_t {
    MoveToCompartment = 0,
    Home = 1,
    EmergencyStop = 2,
    ClearStall = 3
};

struct DispenseCommand {
    DispenseCmdType type;
    uint8_t compartment;
};

extern TaskHandle_t xTaskHeartbeat;
extern TaskHandle_t xTaskSensors;
extern TaskHandle_t xTaskECG;
extern TaskHandle_t xTaskTemp;
extern TaskHandle_t xTaskDispense;
extern TaskHandle_t xTaskTelemetry;

extern QueueHandle_t xQueueSensorData;
extern QueueHandle_t xQueueEvents;
extern QueueHandle_t xQueueDispenseCmd;

void taskHeartbeat(void* pvParameters);
void taskSensors(void* pvParameters);
void taskECG(void* pvParameters);
void taskTemp(void* pvParameters);
void taskDispense(void* pvParameters);
void taskTelemetry(void* pvParameters);

class NetworkManager;
class MqttPublisher;

NetworkManager& getNetworkManager();
MqttPublisher& getMqttPublisher();

inline void initSystemQueues() {
    if (xQueueSensorData == nullptr) {
        xQueueSensorData = xQueueCreate(SENSOR_QUEUE_DEPTH, sizeof(SensorPacket));
    }
    if (xQueueEvents == nullptr) {
        xQueueEvents = xQueueCreate(16, 32);
    }
    if (xQueueDispenseCmd == nullptr) {
        xQueueDispenseCmd = xQueueCreate(8, sizeof(DispenseCommand));
    }
}

#endif
