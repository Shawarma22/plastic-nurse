#include "tasks.h"
#include "ad8232.h"
#include "ecg_filters.h"
#include "sensor_types.h"
#include <Arduino.h>

TaskHandle_t xTaskECG = nullptr;

static AD8232Driver ecgDriver;
static ECGBandpassFilter bpf;
static PanTompkinsDerivative deriv;
static MovingWindowIntegrator<32> mwi;
static ECGPeakDetector peakDetector(250);
static ECGHeartRateCalculator<8> hrCalc;
static ECGContactQuality qualityCalc;

void taskECG(void* pvParameters) {
    if (!ecgDriver.init()) {
        vTaskDelete(nullptr);
        return;
    }

    TickType_t lastWakeTime = xTaskGetTickCount();
    const TickType_t frequency = pdMS_TO_TICKS(4);
    uint32_t seq = 0;

    for (;;) {
        uint16_t raw = ecgDriver.read_raw();
        bool leadsAttached = ecgDriver.are_leads_attached();

        float filtered = bpf.step(static_cast<float>(raw));
        float d = deriv.step(filtered);
        float energy = mwi.step(d);

        float peakVal = 0.0f;
        if (leadsAttached && peakDetector.step(energy, peakVal)) {
            hrCalc.record_peak(millis());
        }

        float bpm = leadsAttached ? hrCalc.get_bpm() : 0.0f;
        float conf = qualityCalc.calculate(
            leadsAttached,
            peakDetector.get_spki(),
            peakDetector.get_npki(),
            raw,
            hrCalc.get_interval_count()
        );

        if (xQueueSensorData != nullptr && (seq % 5 == 0)) {
            SensorPacket packet{};
            packet.sequence_id = ++seq;
            packet.timestamp_ms = millis();
            packet.ecg.raw_signal = raw;
            packet.ecg.filtered_signal = filtered;
            packet.ecg.bpm = bpm;
            packet.ecg.confidence = conf;
            packet.ecg.leads_off = !leadsAttached;
            packet.status_flags = leadsAttached ? FLAG_ECG_CONNECTED : FLAG_ECG_LEAD_OFF;

            xQueueSend(xQueueSensorData, &packet, 0);
        } else {
            seq++;
        }

        vTaskDelayUntil(&lastWakeTime, frequency);
    }
}
