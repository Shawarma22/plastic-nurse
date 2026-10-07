#ifndef MAX30102_REGS_H
#define MAX30102_REGS_H

#include <stdint.h>

static constexpr uint8_t MAX30102_I2C_ADDR = 0x57;
static constexpr uint8_t MAX30102_EXPECTED_PART_ID = 0x15;

static constexpr uint8_t REG_INT_STATUS_1 = 0x00;
static constexpr uint8_t REG_INT_STATUS_2 = 0x01;
static constexpr uint8_t REG_INT_ENABLE_1 = 0x02;
static constexpr uint8_t REG_INT_ENABLE_2 = 0x03;

static constexpr uint8_t REG_FIFO_WR_PTR = 0x04;
static constexpr uint8_t REG_OVF_COUNTER = 0x05;
static constexpr uint8_t REG_FIFO_RD_PTR = 0x06;
static constexpr uint8_t REG_FIFO_DATA = 0x07;

static constexpr uint8_t REG_FIFO_CONFIG = 0x08;
static constexpr uint8_t REG_MODE_CONFIG = 0x09;
static constexpr uint8_t REG_SPO2_CONFIG = 0x0A;

static constexpr uint8_t REG_LED1_PA = 0x0C;
static constexpr uint8_t REG_LED2_PA = 0x0D;

static constexpr uint8_t REG_MULTI_LED_CTRL1 = 0x11;
static constexpr uint8_t REG_MULTI_LED_CTRL2 = 0x12;

static constexpr uint8_t REG_DIE_TEMP_INT = 0x1F;
static constexpr uint8_t REG_DIE_TEMP_FRAC = 0x20;
static constexpr uint8_t REG_DIE_TEMP_CONFIG = 0x21;

static constexpr uint8_t REG_REV_ID = 0xFE;
static constexpr uint8_t REG_PART_ID = 0xFF;

static constexpr uint8_t MASK_MODE_HEARTRATE = 0x02;
static constexpr uint8_t MASK_MODE_SPO2 = 0x03;
static constexpr uint8_t MASK_MODE_MULTI_LED = 0x07;
static constexpr uint8_t MASK_MODE_RESET = 0x40;
static constexpr uint8_t MASK_MODE_SHDN = 0x80;

static constexpr uint8_t MASK_INT_A_FULL = 0x80;
static constexpr uint8_t MASK_INT_PPG_RDY = 0x40;
static constexpr uint8_t MASK_INT_ALC_OVF = 0x20;
static constexpr uint8_t MASK_INT_PWR_RDY = 0x01;

static constexpr uint8_t MASK_SAMPLE_AVG_1 = 0x00;
static constexpr uint8_t MASK_SAMPLE_AVG_2 = 0x20;
static constexpr uint8_t MASK_SAMPLE_AVG_4 = 0x40;
static constexpr uint8_t MASK_SAMPLE_AVG_8 = 0x60;

static constexpr uint8_t MASK_PULSE_WIDTH_69US = 0x00;
static constexpr uint8_t MASK_PULSE_WIDTH_118US = 0x01;
static constexpr uint8_t MASK_PULSE_WIDTH_215US = 0x02;
static constexpr uint8_t MASK_PULSE_WIDTH_411US = 0x03;

static constexpr uint8_t MASK_SAMPLERATE_50HZ = 0x00;
static constexpr uint8_t MASK_SAMPLERATE_100HZ = 0x04;
static constexpr uint8_t MASK_SAMPLERATE_200HZ = 0x08;
static constexpr uint8_t MASK_SAMPLERATE_400HZ = 0x0C;

static constexpr uint8_t MASK_ADC_RGE_2048NA = 0x00;
static constexpr uint8_t MASK_ADC_RGE_4096NA = 0x20;
static constexpr uint8_t MASK_ADC_RGE_8192NA = 0x40;
static constexpr uint8_t MASK_ADC_RGE_16384NA = 0x60;

#endif
