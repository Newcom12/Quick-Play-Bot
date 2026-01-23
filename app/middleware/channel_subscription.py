"""Middleware для проверки подписки на канал."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from loguru import logger

from app.bot import bot
from app.config import settings


class ChannelSubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки на канал."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверяет подписку на канал."""
        if not isinstance(event, Message):
            return await handler(event, data)
        
        # Пропускаем команду /start, там будет отдельная проверка
        if event.text and event.text.startswith('/start'):
            return await handler(event, data)
        
        # Если канал не указан, пропускаем проверку
        if not settings.CHANNEL_ID:
            return await handler(event, data)
        
        try:
            user_id = event.from_user.id
            chat_member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
            
            if chat_member.status in ['left', 'kicked']:
                await event.answer(
                    f"❌ Для использования бота необходимо подписаться на канал:\n"
                    f"👉 {settings.CHANNEL_ID}\n\n"
                    f"После подписки используйте команду /start"
                )
                return
            
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки: {e}")
            # В случае ошибки пропускаем проверку
        
        return await handler(event, data)
