"""Configuration via pydantic-settings — pattern from example/app/database/config.py."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None
    COOKIE_NAME: Optional[str] = "SAFECALL_API"
    SECRET_KEY: Optional[str] = "change-me"
    APP_NAME: Optional[str] = "SafeCall Voice Guard API"
    APP_DESCRIPTION: Optional[str] = "Deepfake voice detection"
    DEBUG: Optional[bool] = False
    API_VERSION: Optional[str] = "1.0"
    # SafeCall-specific (из ДЗ7 threshold_tuning_results.json)
    THRESHOLD: float = 0.37
    MODEL_PATH: str = "/app/weights/best_xlsr_head.pth"
    # RabbitMQ
    RABBITMQ_HOST: Optional[str] = "rabbitmq"
    RABBITMQ_PORT: Optional[int] = 5672
    RABBITMQ_USER: Optional[str] = "rmuser"
    RABBITMQ_PASS: Optional[str] = "rmpassword"
    RABBITMQ_QUEUE: Optional[str] = "safecall_tasks"

    @property
    def DATABASE_URL_psycopg(self):
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    def validate(self):
        if not all([self.DB_HOST, self.DB_USER, self.DB_PASS, self.DB_NAME]):
            raise ValueError("Missing DB configuration. Check .env file.")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings
