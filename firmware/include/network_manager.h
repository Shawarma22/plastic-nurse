#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "config.h"

enum class NetworkState : uint8_t {
    Disconnected = 0,
    Connecting = 1,
    Connected = 2,
    Failed = 3
};

class NetworkManager {
public:
    NetworkManager(
        const char* ssid = WIFI_DEFAULT_SSID,
        const char* password = WIFI_DEFAULT_PASS
    );

    bool init();
    void connect();
    void disconnect();
    bool update();
    bool is_connected() const;
    NetworkState get_state() const;
    int32_t get_rssi() const;
    const char* get_ip_address() const;
    uint32_t get_reconnect_count() const;
    void set_credentials(const char* ssid, const char* password);

private:
    const char* wifi_ssid;
    const char* wifi_password;
    NetworkState state;
    uint32_t last_connect_attempt_ms;
    uint32_t connect_start_ms;
    uint32_t reconnect_count;
    char ip_buffer[16];
};

#endif
