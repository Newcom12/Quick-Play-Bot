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
        "4. Добавьте имена всех игроков\n"
        "5. По очереди открывайте карты\n"
        "6. Обсуждайте и ищите шпионов!\n\n"
        "⏱️ <b>Таймер:</b> 2.5 минуты (настраивается)\n\n"
        "🕵️ <b>Угадывание темы:</b>\n"
        "Шпионы могут угадать тему игры (название карты).\n"
        "Если угадали - победа! Если нет - выбывают.\n\n"
        "🗳️ <b>Голосование:</b>\n"
        "Голосуйте за того, кого считаете шпионом.\n\n"
        "🎯 <b>Правила победы:</b>\n"
        "• Шпион выигрывает, если угадал тему игры\n"
        "• Игроки выигрывают, если нашли всех шпионов\n"
        "• Игра заканчивается когда осталось 2 человека\n\n"
        "📊 <b>Статистика:</b>\n"
        "Просматривайте статистику всех игроков!\n\n"
        "📝 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/spy - Начать игру Шпион\n"
        "/rules - Правила игры\n"
        "/stats - Статистика игроков\n"
        "/help - Эта справка"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_start")]
    ])
    
    # Отправляем помощь с inline кнопкой
    await message.answer(help_text, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    """Возврат в главное меню."""
    from app.handlers.start import cmd_start
    await cmd_start(callback.message)
    await callback.answer()
