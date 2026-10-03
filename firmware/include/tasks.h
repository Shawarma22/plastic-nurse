#ifndef TASKS_H
#define TASKS_H

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include "config.h"

extern TaskHandle_t xTaskHeartbeat;
extern TaskHandle_t xTaskSensors;
extern TaskHandle_t xTaskTelemetry;

extern QueueHandle_t xQueueSensorData;
extern QueueHandle_t xQueueEvents;

void taskHeartbeat(void* pvParameters);
void taskSensors(void* pvParameters);
void taskTelemetry(void* pvParameters);

inline void initSystemQueues() {
    if (xQueueSensorData == nullptr) {
        xQueueSensorData = xQueueCreate(SENSOR_QUEUE_DEPTH, 64);
    }
    if (xQueueEvents == nullptr) {
        xQueueEvents = xQueueCreate(16, 32);
    }
}

#endif
