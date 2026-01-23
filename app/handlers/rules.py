"""Обработчик правил игры."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot import get_main_keyboard

router = Router()


@router.callback_query(F.data == "show_rules")
async def show_rules_callback(callback: CallbackQuery):
    """Обработчик кнопки правил."""
    await cmd_rules(callback.message)
    await callback.answer()


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    """Показывает правила игры Шпион."""
    rules_text = (
        "📖 <b>Правила игры Шпион</b>\n\n"
        
        "🎯 <b>Цель игры:</b>\n"
        "• <b>Обычные игроки:</b> Найти всех шпионов\n"
        "• <b>Шпионы:</b> Не выдать себя и вычислить тему игры\n\n"
        
        "🎮 <b>Как играть:</b>\n"
        "1️⃣ Выберите количество игроков (3-10)\n"
        "2️⃣ Выберите количество шпионов (или используйте случайный выбор 🎲)\n"
        "3️⃣ По очереди открывайте свои карты\n"
        "4️⃣ Обсуждайте тему игры, не называя её напрямую\n"
        "5️⃣ Голосуйте за тех, кого считаете шпионами\n\n"
        
        "🎴 <b>Карты:</b>\n"
        "• Каждый обычный игрок получает карту из игры (например, Clash Royale)\n"
        "• Все обычные игроки видят одинаковую тему (название карты)\n"
        "• Шпионы НЕ знают тему и должны её угадать\n\n"
        
        "⏱️ <b>Таймер:</b>\n"
        "• Игра длится 2.5 минуты (настраивается)\n"
        "• Таймер обновляется каждую секунду\n"
        "• После окончания времени можно начать голосование\n\n"
        
        "🗳️ <b>Голосование:</b>\n"
        "• Выберите игрока, которого считаете шпионом\n"
        "• Если угадали шпиона - он выбывает\n"
        "• Если ошиблись - обычный игрок выбывает\n"
        "• Игра продолжается до окончания\n\n"
        
        "🏆 <b>Условия победы:</b>\n"
        "• <b>Игроки выигрывают:</b> Когда осталось 2 человека и среди них нет шпионов\n"
        "• <b>Шпионы выигрывают:</b> Когда осталось 2 человека и среди них есть хотя бы 1 шпион\n"
        "• Игра заканчивается только когда осталось ровно 2 человека\n\n"
        
        "💡 <b>Советы:</b>\n"
        "• Шпионы должны задавать вопросы, чтобы понять тему\n"
        "• Обычные игроки должны быть осторожны, чтобы не выдать тему\n"
        "• Внимательно следите за поведением других игроков\n"
        "• Используйте логику и интуицию для поиска шпионов\n\n"
        
        "🎲 <b>Случайный выбор:</b>\n"
        "• Используйте кнопку \"🎲 Случайно\" для автоматического выбора количества шпионов\n"
        "• Это добавит элемент неожиданности в игру!\n\n"
        
        "✨ <b>Особенности:</b>\n"
        "• Игра проходит на одном телефоне\n"
        "• Карты берутся из базы данных (например, Clash Royale)\n"
        "• Можно играть с картами из разных игр\n"
        "• Каждая игра уникальна благодаря случайному выбору карт"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_start")]
    ])
    
    # Отправляем правила с inline кнопкой
    await message.answer(rules_text, reply_markup=keyboard)


@router.message(F.text == "📖 Правила")
async def handle_rules_button(message: Message):
    """Обработчик кнопки правил из reply клавиатуры."""
    await cmd_rules(message)


@router.message(F.text == "🎮 Играть в Шпиона")
async def handle_play_button(message: Message, state: FSMContext):
    """Обработчик кнопки игры из reply клавиатуры."""
    from app.handlers.spy_game.handlers import cmd_spy
    await cmd_spy(message, state)


@router.message(F.text == "ℹ️ Помощь")
async def handle_help_button(message: Message):
    """Обработчик кнопки помощи из reply клавиатуры."""
    from app.handlers.help import cmd_help
    await cmd_help(message)
