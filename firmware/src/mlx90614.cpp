#include "mlx90614.h"
#include <Arduino.h>

MLX90614::MLX90614(uint8_t i2c_addr)
    : address(i2c_addr),
      wire(&Wire),
      initialized(false),
      last_ambient_c(0.0f),
      last_object_c(0.0f) {}

bool MLX90614::begin(TwoWire& wire_port) {
    wire = &wire_port;
    wire->beginTransmission(address);
    if (wire->endTransmission() != 0) {
        initialized = false;
        return false;
    }
    initialized = true;
    return true;
}

bool MLX90614::is_connected() const {
    return initialized;
}

uint8_t MLX90614::crc8(const uint8_t* data, size_t len) {
    uint8_t crc = 0x00;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; ++j) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0x07;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

bool MLX90614::read16(uint8_t reg, uint16_t& out_val) {
    if (!initialized || wire == nullptr) {
        return false;
    }

    wire->beginTransmission(address);
    wire->write(reg);
    if (wire->endTransmission(false) != 0) {
        return false;
    }

    if (wire->requestFrom(static_cast<uint8_t>(address), static_cast<uint8_t>(3)) != 3) {
        return false;
    }

    uint8_t lsb = wire->read();
    uint8_t msb = wire->read();
    uint8_t pec = wire->read();

    uint8_t check_buf[5] = {
        static_cast<uint8_t>(address << 1),
        reg,
        static_cast<uint8_t>((address << 1) | 1),
        lsb,
        msb
    };

    if (crc8(check_buf, 5) != pec) {
        return false;
    }

    out_val = static_cast<uint16_t>(lsb) | (static_cast<uint16_t>(msb) << 8);
    return true;
}

uint16_t MLX90614::read_raw_temp(uint8_t reg) {
    uint16_t raw = 0;
    if (!read16(reg, raw)) {
        return 0;
    }
    return raw;
}

float MLX90614::read_ambient_temp_c() {
    uint16_t raw = read_raw_temp(MLX90614_REG_TA);
    if (raw == 0 || (raw & 0x8000) != 0) {
        return -999.0f;
    }
    float kelvin = static_cast<float>(raw) * MLX90614_TEMP_RES;
    last_ambient_c = kelvin - MLX90614_KELVIN_OFFSET;
    return last_ambient_c;
}

float MLX90614::get_last_ambient_c() const {
    return last_ambient_c;
}

float MLX90614::read_object_temp_c() {
    uint16_t raw = read_raw_temp(MLX90614_REG_TOBJ1);
    if (raw == 0 || (raw & 0x8000) != 0) {
        return -999.0f;
    }
    float kelvin = static_cast<float>(raw) * MLX90614_TEMP_RES;
    last_object_c = kelvin - MLX90614_KELVIN_OFFSET;
    return last_object_c;
}

float MLX90614::get_last_object_c() const {
    return last_object_c;
}

float MLX90614::read_object2_temp_c() {
    uint16_t raw = read_raw_temp(MLX90614_REG_TOBJ2);
    if (raw == 0 || (raw & 0x8000) != 0) {
        return -999.0f;
    }
    float kelvin = static_cast<float>(raw) * MLX90614_TEMP_RES;
    return kelvin - MLX90614_KELVIN_OFFSET;
}

bool MLX90614::write16(uint8_t reg, uint16_t val) {
    if (!initialized || wire == nullptr) {
        return false;
    }

    uint8_t lsb = static_cast<uint8_t>(val & 0xFF);
    uint8_t msb = static_cast<uint8_t>((val >> 8) & 0xFF);

    uint8_t check_buf[4] = {
        static_cast<uint8_t>(address << 1),
        reg,
        lsb,
        msb
    };
    uint8_t pec = crc8(check_buf, 4);

    wire->beginTransmission(address);
    wire->write(reg);
    wire->write(lsb);
    wire->write(msb);
    wire->write(pec);
    return (wire->endTransmission() == 0);
}

float MLX90614::read_emissivity() {
    uint16_t raw = 0;
    if (!read16(MLX90614_REG_EMISSIVITY, raw)) {
        return 0.0f;
    }
    return static_cast<float>(raw) / 65535.0f;
}

bool MLX90614::write_emissivity(float emissivity) {
    if (emissivity < 0.1f || emissivity > 1.0f) {
        return false;
    }
    uint16_t raw = static_cast<uint16_t>(emissivity * 65535.0f + 0.5f);
    if (!write16(MLX90614_REG_EMISSIVITY, 0x0000)) {
        return false;
    }
    delay(10);
    if (!write16(MLX90614_REG_EMISSIVITY, raw)) {
        return false;
    }
    delay(10);
    return true;
}



