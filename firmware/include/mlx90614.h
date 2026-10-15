#ifndef MLX90614_H
#define MLX90614_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <Wire.h>
#include "mlx90614_regs.h"

class MLX90614 {
public:
    MLX90614(uint8_t i2c_addr = MLX90614_DEFAULT_I2C_ADDR);

    bool begin(TwoWire& wire_port = Wire);
    bool is_connected() const;
    float read_ambient_temp_c();
    float get_last_ambient_c() const;
    float read_object_temp_c();
    uint16_t read_raw_temp(uint8_t reg);
    bool write_emissivity(float emissivity);
    float read_emissivity();
    static uint8_t crc8(const uint8_t* data, size_t len);

private:
    uint8_t address;
    TwoWire* wire;
    bool initialized;
    float last_ambient_c;
    float last_object_c;

    bool read16(uint8_t reg, uint16_t& out_val);
    bool write16(uint8_t reg, uint16_t val);
};

#endif
