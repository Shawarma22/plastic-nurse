#include <Arduino.h>
#include "config.h"
#include "pinout.h"

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_LED_STATUS, OUTPUT);
    digitalWrite(PIN_LED_STATUS, LOW);
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
