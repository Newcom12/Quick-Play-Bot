"""Точка входа в приложение."""

import asyncio

from app.bot import bot, dp, on_startup, on_shutdown
from app.database import init_db
from app.handlers import start, help
from app.handlers import rules
from app.handlers.spy_game import handlers as spy_game_handlers
from app.middleware.channel_subscription import ChannelSubscriptionMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.utils.logger import logger


async def main():
    """Главная функция запуска бота."""
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        await init_db()
        logger.info("База данных успешно инициализирована")

        # Регистрация middleware
        dp.message.middleware(RateLimitMiddleware(rate_limit=0.5))
        dp.callback_query.middleware(RateLimitMiddleware(rate_limit=0.5))
        dp.message.middleware(ChannelSubscriptionMiddleware())
        logger.info("Middleware успешно зарегистрированы")
        
        # Регистрация роутеров
        dp.include_router(start.router)
        dp.include_router(help.router)
        dp.include_router(rules.router)
        from app.handlers import stats
        dp.include_router(stats.router)
        dp.include_router(spy_game_handlers.router)
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
