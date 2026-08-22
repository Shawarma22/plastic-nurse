from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    DROID_HAL: Literal["mock", "real"] = "mock"
    DROID_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = "supersecretkeyformockenvironmentonly32bytesmin"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./droid.db"
    BCRYPT_ROUNDS: int = 4
    MOTOR_WATCHDOG_TIMEOUT_SEC: float = 1.5
    CAMERA_FPS: int = 15
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
