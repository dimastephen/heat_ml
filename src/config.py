from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Heat Forecast"
    APP_ENV: str = "DEV"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    #DB
    POSTGRES_URL: str =""
    TIMESCALEDB_URL: str=""

    #AUTH
    JWT_SECRET_KEY: str
    JWT_ALGO_SECRET_KEY: str = "HS256"
    JWT_ACCESS_TIME_MINS: int = 15
    JWT_REFRESH_TIME_DAYS: int = 7

    #FILES
    FILE_STORAGE_PATH: str = "uploads"
    FILE_PREPARED_PATH: str = "prepared"
    MODEL_STORAGE_PATH: str = "models"

    #QUEUE
    REDIS_URL: str = "redis://localhost:6379/0"

    #LOGGING
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/app.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="UTF-8")

@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
