#ifndef PACKET_SERIALIZER_H
#define PACKET_SERIALIZER_H

#include <stddef.h>
#include <stdbool.h>
#include "sensor_types.h"

size_t serializeSensorPacket(const SensorPacket& packet, char* buffer, size_t bufferSize);
bool deserializeSensorPacket(const char* json, SensorPacket& packet);

#endif
