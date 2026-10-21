from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

INSECURE_DEFAULT_SECRET_KEY = "supersecretkeyformockenvironmentonly32bytesmin"

class Settings(BaseSettings):
    DROID_HAL: Literal["mock", "real"] = "mock"
    DROID_ENV: Literal["development", "staging", "production"] = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = INSECURE_DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./droid.db"
    BCRYPT_ROUNDS: int = 12
    INITIAL_ADMIN_PASSWORD: str | None = None
    MOTOR_WATCHDOG_TIMEOUT_SEC: float = 1.5
    CAMERA_FPS: int = 15
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "droid-rpi-core"
    MQTT_TOPIC_STATUS: str = "droid/status"
    MQTT_TOPIC_VITALS_PROCESSED: str = "droid/vitals/processed"
    MQTT_TOPIC_VITALS_RAW: str = "droid/vitals/raw"
    MQTT_TOPIC_VITALS_EVENTS: str = "droid/vitals/events"
    MQTT_TOPIC_CMD_DISPENSE: str = "droid/cmd/dispense"
    MQTT_INGEST_ENABLED: bool = True
    MQTT_INGEST_BATCH_SIZE: int = 25
    MQTT_INGEST_FLUSH_INTERVAL_SEC: float = 1.0
    MQTT_KEEPALIVE_SEC: int = 60
    BLE_BP_ENABLED: bool = True
    BLE_BP_DEVICE_NAME_PREFIX: str = "BP_"
    BLE_BP_DEVICE_MAC: str | None = None
    BLE_BP_SCAN_TIMEOUT_SEC: float = 10.0
    BLE_BP_RECONNECT_INTERVAL_SEC: float = 5.0
    BLE_BP_UUID_SERVICE: str = "00001810-0000-1000-8000-00805f9b34fb"
    BLE_BP_UUID_CHAR_MEASUREMENT: str = "00002a35-0000-1000-8000-00805f9b34fb"
    ALERT_HEART_RATE_MIN: float = 45.0
    ALERT_HEART_RATE_MAX: float = 130.0
    ALERT_SPO2_MIN: float = 90.0
    ALERT_TEMP_OBJECT_MAX_C: float = 38.5
    ALERT_TEMP_OBJECT_MIN_C: float = 35.0
    ALERT_BP_SYSTOLIC_MAX: float = 160.0
    ALERT_BP_SYSTOLIC_MIN: float = 85.0
    ALERT_BP_DIASTOLIC_MAX: float = 100.0
    ALERT_BP_DIASTOLIC_MIN: float = 50.0
    ALERT_CONFIDENCE_THRESHOLD: float = 0.50
    ALERT_COOLDOWN_SEC: float = 10.0
    PIN_MOTOR_L_FWD: int = 17
    PIN_MOTOR_L_BWD: int = 27
    PIN_MOTOR_L_PWM: int = 18
    PIN_MOTOR_R_FWD: int = 22
    PIN_MOTOR_R_BWD: int = 23
    PIN_MOTOR_R_PWM: int = 13
    PIN_DOOR_OPEN: int = 24
    PIN_DOOR_CLOSE: int = 25
    PIN_DOOR_LIMIT_OPEN: int = 5
    PIN_DOOR_LIMIT_CLOSED: int = 6
    PIN_ESTOP: int = 26
    VOSK_MODEL_PATH: str = "models/vosk"
    AUDIO_SAMPLE_RATE: int = 16000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def _reject_insecure_defaults_outside_dev(self) -> "Settings":
        if self.DROID_ENV != "development":
            if self.SECRET_KEY == INSECURE_DEFAULT_SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY must be overridden via environment when DROID_ENV is not 'development'"
                )
            if self.BCRYPT_ROUNDS < 12:
                raise ValueError(
                    "BCRYPT_ROUNDS must be >= 12 when DROID_ENV is not 'development'"
                )
        return self

settings = Settings()
