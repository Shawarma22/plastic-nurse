#include "tasks.h"
#include "max30102.h"
#include "dsp_filters.h"
#include "sensor_types.h"
#include "status_led.h"
#include <Arduino.h>

static MAX30102 ppgSensor;
static DCRemovalFilter dcRed(0.95f);
static DCRemovalFilter dcIR(0.95f);
static MovingAverageFilter<5> lpfRed;
static MovingAverageFilter<5> lpfIR;
static PeakDetector peakDetector(30, 25.0f);
static HeartRateEstimator<8> hrEstimator(100.0f);
static RatioCalculator ratioCalc;
static SpO2Estimator spo2Estimator;
static PerfusionIndexEstimator piEstimator;
static FingerDetector fingerDetector(50000);

void taskSensors(void* pvParameters) {
    if (!ppgSensor.begin()) {
        vTaskDelete(nullptr);
        return;
    }

    ppgSensor.setup();
    setLedState(LedId::Sensor, true);

    uint32_t redBuffer[16];
    uint32_t irBuffer[16];
    uint32_t seq = 0;

    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t frequency = pdMS_TO_TICKS(10);

    for (;;) {
        uint8_t samplesRead = ppgSensor.readFIFO(redBuffer, irBuffer, 16);
        for (uint8_t i = 0; i < samplesRead; ++i) {
            uint32_t rawRed = redBuffer[i];
            uint32_t rawIR = irBuffer[i];

            bool fingerPresent = fingerDetector.update(rawIR);

            float acRed = lpfRed.step(dcRed.step(static_cast<float>(rawRed)));
            float acIR = lpfIR.step(dcIR.step(static_cast<float>(rawIR)));

            if (peakDetector.step(acIR)) {
                hrEstimator.addInterval(peakDetector.getSamplesSincePeak());
            }

            ratioCalc.update(acRed, dcRed.getDC(), acIR, dcIR.getDC());
            float ratio = ratioCalc.getRatio();
            float spo2 = spo2Estimator.calculate(ratio);
            piEstimator.update(acIR, dcIR.getDC());

            if (xQueueSensorData != nullptr) {
                SensorPacket packet{};
                packet.sequence_id = ++seq;
                packet.timestamp_ms = millis();
                packet.ppg.ir_raw = rawIR;
                packet.ppg.red_raw = rawRed;
                packet.ppg.bpm = fingerPresent ? hrEstimator.getBPM() : 0.0f;
                packet.ppg.spo2 = fingerPresent ? spo2 : 0.0f;
                packet.ppg.confidence = fingerPresent ? piEstimator.getConfidence() : 0.0f;
                packet.ppg.finger_detected = fingerPresent;
                packet.status_flags = fingerPresent ? (FLAG_PPG_CONNECTED | FLAG_PPG_FINGER_DETECTED) : FLAG_PPG_CONNECTED;

                xQueueSend(xQueueSensorData, &packet, 0);
            }
        }

        vTaskDelayUntil(&lastWakeTime, frequency);
    }
}
