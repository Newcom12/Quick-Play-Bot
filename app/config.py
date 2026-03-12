"""Конфигурация приложения через pydantic_settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Токен Telegram-бота
    BOT_TOKEN: str

    # База данных PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://quickplay:quickplay@postgres:5432/quickplaybot"

    # Редис для машины состояний
    REDIS_URL: str = "redis://redis:6379/0"

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app/data/logs/bot.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "7 days"
    
    # Настройки игры
    CHANNEL_ID: str = ""  # Идентификатор канала для проверки подписки (например: "@channel" или "-1001234567890")
    GAME_TIMER_DURATION: int = 150  # Длительность игры в секундах (по умолчанию 2.5 минуты)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
