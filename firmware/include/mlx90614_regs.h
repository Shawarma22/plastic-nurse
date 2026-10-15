#ifndef MLX90614_REGS_H
#define MLX90614_REGS_H

#include <stdint.h>

static constexpr uint8_t MLX90614_DEFAULT_I2C_ADDR = 0x5A;

static constexpr uint8_t MLX90614_CMD_RAM = 0x00;
static constexpr uint8_t MLX90614_CMD_EEPROM = 0x20;

static constexpr uint8_t MLX90614_REG_RAW_DATA_1 = 0x04;
static constexpr uint8_t MLX90614_REG_RAW_DATA_2 = 0x05;
static constexpr uint8_t MLX90614_REG_TA = 0x06;
static constexpr uint8_t MLX90614_REG_TOBJ1 = 0x07;
static constexpr uint8_t MLX90614_REG_TOBJ2 = 0x08;

static constexpr uint8_t MLX90614_REG_TOMAX = 0x20;
static constexpr uint8_t MLX90614_REG_TOMIN = 0x21;
static constexpr uint8_t MLX90614_REG_PWMCTRL = 0x22;
static constexpr uint8_t MLX90614_REG_TARANGE = 0x23;
static constexpr uint8_t MLX90614_REG_EMISSIVITY = 0x24;
static constexpr uint8_t MLX90614_REG_CONFIG_1 = 0x25;
static constexpr uint8_t MLX90614_REG_SMBUS_ADDR = 0x2E;
static constexpr uint8_t MLX90614_REG_ID1 = 0x3C;
static constexpr uint8_t MLX90614_REG_ID2 = 0x3D;
static constexpr uint8_t MLX90614_REG_ID3 = 0x3E;
static constexpr uint8_t MLX90614_REG_ID4 = 0x3F;

static constexpr uint8_t MLX90614_CMD_SLEEP = 0xFF;

static constexpr float MLX90614_TEMP_RES = 0.02f;
static constexpr float MLX90614_KELVIN_OFFSET = 273.15f;

#endif
