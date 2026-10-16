#include "network_manager.h"
#include <WiFi.h>

NetworkManager::NetworkManager(const char* ssid, const char* password)
    : wifi_ssid(ssid),
      wifi_password(password),
      state(NetworkState::Disconnected),
      last_connect_attempt_ms(0),
      connect_start_ms(0),
      reconnect_count(0) {
    ip_buffer[0] = '\0';
}

bool NetworkManager::init() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(false);
    disconnect();
    state = NetworkState::Disconnected;
    return true;
}

void NetworkManager::connect() {
    if (state == NetworkState::Connected || state == NetworkState::Connecting) {
        return;
    }
    WiFi.begin(wifi_ssid, wifi_password);
    state = NetworkState::Connecting;
    connect_start_ms = millis();
    last_connect_attempt_ms = millis();
}

void NetworkManager::disconnect() {
    WiFi.disconnect(true);
    state = NetworkState::Disconnected;
    ip_buffer[0] = '\0';
}

bool NetworkManager::update() {
    uint32_t now = millis();

    switch (state) {
        case NetworkState::Disconnected:
            if (now - last_connect_attempt_ms >= WIFI_RECONNECT_INTERVAL_MS) {
                connect();
            }
            break;

        case NetworkState::Connecting:
            if (WiFi.status() == WL_CONNECTED) {
                state = NetworkState::Connected;
                String ip = WiFi.localIP().toString();
                strncpy(ip_buffer, ip.c_str(), sizeof(ip_buffer) - 1);
                ip_buffer[sizeof(ip_buffer) - 1] = '\0';
            } else if (now - connect_start_ms >= WIFI_CONNECT_TIMEOUT_MS) {
                state = NetworkState::Failed;
                last_connect_attempt_ms = now;
                reconnect_count++;
            }
            break;

        case NetworkState::Connected:
            if (WiFi.status() != WL_CONNECTED) {
                state = NetworkState::Disconnected;
                last_connect_attempt_ms = now;
                ip_buffer[0] = '\0';
                reconnect_count++;
            }
            break;

        case NetworkState::Failed:
            if (now - last_connect_attempt_ms >= WIFI_RECONNECT_INTERVAL_MS) {
                connect();
            }
            break;
    }

    return is_connected();
}

bool NetworkManager::is_connected() const {
    return (state == NetworkState::Connected);
}

NetworkState NetworkManager::get_state() const {
    return state;
}

int32_t NetworkManager::get_rssi() const {
    if (state == NetworkState::Connected) {
        return WiFi.RSSI();
    }
    return -100;
}

const char* NetworkManager::get_ip_address() const {
    return ip_buffer;
}

uint32_t NetworkManager::get_reconnect_count() const {
    return reconnect_count;
}

void NetworkManager::set_credentials(const char* ssid, const char* password) {
    wifi_ssid = ssid;
    wifi_password = password;
    if (is_connected()) {
        disconnect();
    }
}
