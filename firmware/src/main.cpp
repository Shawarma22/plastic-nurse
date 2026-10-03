#include <Arduino.h>
#include "config.h"
#include "pinout.h"
#include "status_led.h"
#include "tasks.h"

void setup() {
    Serial.begin(SERIAL_BAUD);
    initStatusLeds();
    initSystemQueues();

    xTaskCreatePinnedToCore(
        taskHeartbeat,
        "heartbeat",
        STACK_SIZE_HEARTBEAT,
        nullptr,
        PRIORITY_HEARTBEAT,
        &xTaskHeartbeat,
        1
    );
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
