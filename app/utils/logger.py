"""Настройка логирования через loguru."""

import sys
from pathlib import Path
from loguru import logger

from app.config import settings

# Создание директории для логов
log_dir = Path(settings.LOG_FILE).parent
log_dir.mkdir(parents=True, exist_ok=True)

# Удаление стандартного обработчика
logger.remove()

# Добавление консольного обработчика
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
)

# Добавление файлового обработчика
logger.add(
    settings.LOG_FILE,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.LOG_LEVEL,
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    compression="zip",
    encoding="utf-8",
)

__all__ = ["logger"]
