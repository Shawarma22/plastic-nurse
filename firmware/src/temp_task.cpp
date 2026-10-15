#include "tasks.h"
#include "mlx90614.h"
#include "temp_filters.h"
#include "sensor_types.h"
#include <Arduino.h>

TaskHandle_t xTaskTemp = nullptr;

static MLX90614Driver tempDriver;
static TemperaturePlausibilityFilter plausibilityFilter;
static TemperatureMovingAverage<8> movingAverage;
static TemperatureConfidenceEstimator confEstimator;

void taskTemp(void* pvParameters) {
    if (!tempDriver.init()) {
        vTaskDelete(nullptr);
        return;
    }

    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t frequency = pdMS_TO_TICKS(100);
    uint32_t seq = 0;

    for (;;) {
        float rawAmbient = 0.0f;
        float rawObject = 0.0f;
        bool readOk = tempDriver.read_ambient_temp_c(rawAmbient) &&
                      tempDriver.read_object_temp_c(rawObject);

        if (readOk) {
            float filteredObj = plausibilityFilter.filter(rawObject);
            float smoothedObj = movingAverage.step(filteredObj);
            float variance = movingAverage.get_variance();
            bool stable = movingAverage.is_stable();
            float confidence = confEstimator.calculate(rawAmbient, smoothedObj, variance, stable);
            bool targetPresent = confEstimator.is_target_present();

            if (xQueueSensorData != nullptr) {
                SensorPacket packet{};
                packet.sequence_id = ++seq;
                packet.timestamp_ms = millis();
                packet.temp.ambient_c = rawAmbient;
                packet.temp.object_c = smoothedObj;
                packet.temp.confidence = confidence;
                packet.temp.target_present = targetPresent;
                packet.status_flags = FLAG_TEMP_CONNECTED | (targetPresent ? FLAG_TEMP_TARGET_DETECTED : FLAG_NONE);

                xQueueSend(xQueueSensorData, &packet, 0);
            }
        }

        vTaskDelayUntil(&lastWakeTime, frequency);
    }
}
