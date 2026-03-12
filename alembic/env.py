"""Асинхронная конфигурация Alembic."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Импорт настроек и моделей
from app.config import settings
from app.database import Base
from app.models import User, ClashRoyaleCard, SpyCard, PlayerStats, SavedPlayer  # noqa: F401

# Объект конфигурации Alembic, дающий доступ к значениям из .ini файла.
config = context.config

# Интерпретация файла конфигурации для логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Установка URL базы данных из настроек
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Метаданные моделей для поддержки autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запускает миграции в офлайн-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполнение миграций."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Выполнение асинхронных миграций."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запускает миграции в онлайн-режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
