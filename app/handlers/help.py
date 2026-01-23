"""Обработчик команды /help."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка команды /help с информацией о боте."""
    help_text = """
<b>ℹ️ Справка по использованию бота</b>

<b>📋 Доступные команды:</b>
/start - Начать работу с ботом
/help - Показать эту справку

<b>💡 Как использовать:</b>
Просто отправьте одну из команд выше, и бот ответит вам!

<b>❓ Нужна помощь?</b>
Если у вас возникли вопросы или проблемы, обратитесь к администратору бота.

<i>Приятного использования! 🎉</i>
    """.strip()

    await message.answer(help_text)
