#ifndef AD8232_H
#define AD8232_H

#include <stdint.h>
#include <stdbool.h>
#include "pinout.h"
#include "config.h"

static constexpr uint16_t AD8232_DEFAULT_SAMPLE_RATE = AD8232_SAMPLE_RATE_HZ;
static constexpr uint16_t AD8232_BUFFER_CAPACITY = 128;
static constexpr uint16_t AD8232_ADC_MAX_VALUE = 4095;
static constexpr float AD8232_VREF = 3.3f;

class AD8232Driver {
public:
    AD8232Driver(
        uint8_t pin_out = PIN_AD8232_OUT,
        uint8_t pin_lo_plus = PIN_AD8232_LO_PLUS,
        uint8_t pin_lo_minus = PIN_AD8232_LO_MINUS,
        uint8_t pin_sdn = PIN_AD8232_SDN
    );

    bool init();
    uint16_t read_raw();
    bool are_leads_attached();
    bool is_lo_plus_active() const;
    bool is_lo_minus_active() const;
    uint8_t get_leads_status() const;
    bool is_connected() const;
    uint16_t get_sample_rate() const;
    void shutdown();
    void resume();
    void reset();

private:
    uint8_t pin_out;
    uint8_t pin_lo_plus;
    uint8_t pin_lo_minus;
    uint8_t pin_sdn;
    bool initialized;
    bool leads_attached;
    uint16_t last_raw_sample;
};

#endif
