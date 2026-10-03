#include "tasks.h"
#include "status_led.h"
#include <Arduino.h>

TaskHandle_t xTaskHeartbeat = nullptr;
TaskHandle_t xTaskSensors = nullptr;
TaskHandle_t xTaskTelemetry = nullptr;

QueueHandle_t xQueueSensorData = nullptr;
QueueHandle_t xQueueEvents = nullptr;

void taskHeartbeat(void* pvParameters) {
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(500);

    for (;;) {
        toggleLed(LedId::Status);
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}
