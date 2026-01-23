"""Middleware для ограничения частоты запросов."""

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from loguru import logger


class RateLimitMiddleware(BaseMiddleware):
    """Middleware для ограничения частоты сообщений (0.5 секунды)."""
    
    def __init__(self, rate_limit: float = 0.5):
        """
        Args:
            rate_limit: Минимальный интервал между сообщениями в секундах
        """
        self.rate_limit = rate_limit
        self.last_message_time: Dict[int, float] = defaultdict(float)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверяет частоту сообщений."""
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user_id = event.from_user.id
        current_time = time.time()
        last_time = self.last_message_time[user_id]
        
        if current_time - last_time < self.rate_limit:
            time_to_wait = self.rate_limit - (current_time - last_time)
            logger.debug(f"Rate limit для пользователя {user_id}: ожидание {time_to_wait:.2f} сек")
            await event.answer("⏳ Пожалуйста, подождите немного перед следующим действием.")
            return
        
        self.last_message_time[user_id] = current_time
        return await handler(event, data)
