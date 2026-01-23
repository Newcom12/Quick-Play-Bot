"""Точка входа в приложение."""

import asyncio

from app.bot import bot, dp, on_startup, on_shutdown
from app.database import init_db
from app.handlers import start, help
from app.utils.logger import logger


async def main():
    """Главная функция запуска бота."""
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_db()
        logger.info("База данных успешно инициализирована")

        # Регистрация роутеров
        dp.include_router(start.router)
        dp.include_router(help.router)
        logger.info("Роутеры успешно зарегистрированы")

        # Запуск бота
        await on_startup()
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=False)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
