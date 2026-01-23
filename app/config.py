"""Конфигурация приложения через pydantic_settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Telegram Bot Token
    BOT_TOKEN: str

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app/data/bot.db"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app/data/logs/bot.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "7 days"
    
    # Game settings
    CHANNEL_ID: str = ""  # ID канала для проверки подписки (например: "@channel" или "-1001234567890")
    GAME_TIMER_DURATION: int = 150  # Длительность игры в секундах (по умолчанию 2.5 минуты)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
