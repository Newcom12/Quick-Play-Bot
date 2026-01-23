"""Обработчик команды /help."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()


@router.callback_query(F.data == "show_help")
async def show_help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи."""
    await cmd_help(callback.message)
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    help_text = (
        "📖 <b>Помощь по боту</b>\n\n"
        "🎮 <b>Игра Шпион</b>\n"
        "Игра для компании на одном телефоне!\n\n"
        "📋 <b>Как играть:</b>\n"
        "1. Нажмите 'Играть в Шпиона'\n"
        "2. Выберите количество игроков (3-10)\n"
        "3. Выберите количество шпионов\n"
        "4. По очереди открывайте карты\n"
        "5. Обсуждайте и ищите шпионов!\n\n"
        "⏱️ <b>Таймер:</b> 2.5 минуты (настраивается)\n\n"
        "🗳️ <b>Голосование:</b>\n"
        "Голосуйте за того, кого считаете шпионом.\n\n"
        "🎯 <b>Правила победы:</b>\n"
        "• Игроки выигрывают, если найдут всех шпионов\n"
        "• Шпионы выигрывают, если их осталось больше или равно обычным игрокам\n\n"
        "📝 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/spy - Начать игру Шпион\n"
        "/help - Эта справка"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
    ])
    
    await message.answer(help_text, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    """Возврат в главное меню."""
    from app.handlers.start import cmd_start
    await cmd_start(callback.message)
    await callback.answer()
