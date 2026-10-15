#include "tasks.h"
#include "stepper.h"
#include "sensor_types.h"
#include <Arduino.h>

TaskHandle_t xTaskDispense = nullptr;
QueueHandle_t xQueueDispenseCmd = nullptr;

static StepperDriver stepper;

void taskDispense(void* pvParameters) {
    if (!stepper.init()) {
        vTaskDelete(nullptr);
        return;
    }

    stepper.home();

    DispenseCommand cmd{};
    const TickType_t delayTicks = pdMS_TO_TICKS(1);

    for (;;) {
        if (xQueueDispenseCmd != nullptr) {
            if (xQueueReceive(xQueueDispenseCmd, &cmd, 0) == pdTRUE) {
                switch (cmd.type) {
                    case DispenseCmdType::MoveToCompartment:
                        stepper.move_to_compartment(cmd.compartment);
                        break;
                    case DispenseCmdType::Home:
                        stepper.home();
                        break;
                    case DispenseCmdType::EmergencyStop:
                        stepper.emergency_stop();
                        break;
                    case DispenseCmdType::ClearStall:
                        stepper.clear_stall();
                        break;
                }
            }
        }

        if (stepper.is_moving()) {
            stepper.update();
        }

        vTaskDelay(delayTicks);
    }
}
