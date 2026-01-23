"""Обработчики игры Шпион."""

import asyncio
import uuid
from typing import List

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import get_db
from app.handlers.spy_game.game_manager import game_manager
from app.handlers.spy_game.states import SpyGameStates
from app.models import ClashRoyaleCard, SpyCard
from app.utils.logger import logger
from sqlalchemy import select, and_

router = Router()


def create_number_keyboard(min_val: int, max_val: int, callback_prefix: str, add_random: bool = False) -> InlineKeyboardMarkup:
    """Создает клавиатуру с числами."""
    buttons = []
    row = []
    
    for i in range(min_val, max_val + 1):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"{callback_prefix}:{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    # Добавляем кнопку "Случайно" если нужно
    if add_random:
        buttons.append([InlineKeyboardButton(text="🎲 Случайно", callback_data=f"{callback_prefix}:random")])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "start_spy_game")
async def start_spy_game_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки начала игры."""
    await cmd_spy(callback.message, state)
    await callback.answer()


@router.message(Command("spy"))
async def cmd_spy(message: Message, state: FSMContext):
    """Команда для начала игры Шпион."""
    game_id = str(uuid.uuid4())[:8]
    game = game_manager.create_game(message.from_user.id, game_id)
    
    await state.update_data(game_id=game_id)
    await state.set_state(SpyGameStates.waiting_for_players_count)
    
    keyboard = create_number_keyboard(3, 10, "players_count")
    
    await message.answer(
        "🎮 <b>Игра Шпион</b>\n\n"
        "👥 Выберите количество игроков:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("players_count:"), StateFilter(SpyGameStates.waiting_for_players_count))
async def set_players_count(callback: CallbackQuery, state: FSMContext):
    """Устанавливает количество игроков."""
    players_count = int(callback.data.split(":")[1])
    
    await state.update_data(players_count=players_count)
    await state.set_state(SpyGameStates.waiting_for_spies_count)
    
    # Разрешаем выбрать от 1 до players_count (включительно) - можно выбрать всех как шпионов
    keyboard = create_number_keyboard(1, players_count, "spies_count", add_random=True)
    
    await callback.message.edit_text(
        f"✅ Игроков: <b>{players_count}</b>\n\n"
        "🕵️ Выберите количество шпионов:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("spies_count:"), StateFilter(SpyGameStates.waiting_for_spies_count))
async def set_spies_count(callback: CallbackQuery, state: FSMContext):
    """Устанавливает количество шпионов."""
    data = await state.get_data()
    players_count = data.get("players_count")
    
    # Проверяем, выбран ли случайный вариант
    if callback.data.endswith(":random"):
        import random
        # Случайное количество шпионов от 1 до players_count (включительно)
        spies_count = random.randint(1, players_count)
    else:
        spies_count = int(callback.data.split(":")[1])
    
    # Не показываем количество шпионов игрокам (для интриги)
    if callback.data.endswith(":random"):
        await callback.message.edit_text(
            f"✅ Игроков: <b>{players_count}</b>\n"
            f"🎲 Количество шпионов выбрано случайно\n\n"
            "⏳ Настраиваю игру..."
        )
    else:
        await callback.message.edit_text(
            f"✅ Игроков: <b>{players_count}</b>\n"
            f"🕵️ Количество шпионов настроено\n\n"
            "⏳ Настраиваю игру..."
        )
    
    await state.update_data(spies_count=spies_count)
    
    # Загружаем карты из базы данных
    cards_list = []
    async for db in get_db():
        try:
            # Загружаем все карты из БД
            result = await db.execute(select(ClashRoyaleCard))
            all_cards = result.scalars().all()
            
            logger.info(f"Всего карт в БД: {len(all_cards)}")
            
            # Фильтруем карты с file_id
            cards_list = [
                {"name": card.name, "file_id": card.file_id} 
                for card in all_cards 
                if card.file_id and card.file_id.strip()
            ]
            
            logger.info(f"Карт с file_id: {len(cards_list)}")
            
            if not cards_list and all_cards:
                logger.warning(
                    f"В БД есть {len(all_cards)} карт, но ни у одной нет file_id. "
                    f"Возможно, нужно загрузить file_id через upload_cards_to_bot."
                )
        except Exception as e:
            logger.error(f"Ошибка при загрузке карт из БД: {e}", exc_info=True)
        break
    
    if not cards_list:
        await callback.message.edit_text(
            "❌ Карты не найдены в базе данных. Пожалуйста, сначала загрузите карты."
        )
        await callback.answer()
        await state.clear()
        return
    
    # Настраиваем игру
    game = game_manager.setup_game(
        callback.from_user.id,
        players_count,
        spies_count,
        cards_list
    )
    
    if not game:
        await callback.message.edit_text("❌ Ошибка при создании игры")
        await callback.answer()
        await state.clear()
        return
    
    await state.set_state(SpyGameStates.showing_cards)
    await state.update_data(current_player_index=0)
    
    # Показываем карту первому игроку
    await show_player_card(callback.message, state, game)
    await callback.answer()


async def show_player_card(message, state: FSMContext, game):
    """Показывает карту текущему игроку."""
    current_player = game.get_current_player()
    
    if not current_player:
        # Все игроки увидели карты, начинаем игру
        await start_game(message, state, game)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁️ Открыть карту", callback_data="show_card")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")]
    ])
    
    text = (
        f"👤 <b>Игрок {game.current_player_index + 1}</b>\n\n"
        "Нажмите кнопку, чтобы увидеть свою карту:"
    )
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "show_card", StateFilter(SpyGameStates.showing_cards))
async def handle_show_card(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает показ карты игроку."""
    game = game_manager.get_game(callback.from_user.id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    
    current_player = game.get_current_player()
    if not current_player:
        await callback.answer("Ошибка", show_alert=True)
        return
    
    current_player.has_seen_card = True
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🙈 Скрыть карту", callback_data="hide_card")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")]
    ])
    
    if current_player.is_spy:
        # Каждый шпион видит обычное сообщение, не зная что все шпионы
        text = (
            "🕵️ <b>ВЫ ШПИОН!</b>\n\n"
            "Ваша задача - не выдать себя и вычислить тему игры."
        )
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        text = f"🎴 <b>Ваша карта:</b> {current_player.card_name}"
        await callback.message.edit_text(text, reply_markup=keyboard)
        if current_player.file_id:
            await callback.message.answer_photo(
                current_player.file_id,
                caption=f"🎴 {current_player.card_name}"
            )
    
    await callback.answer()


@router.callback_query(F.data == "hide_card", StateFilter(SpyGameStates.showing_cards))
async def handle_hide_card(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает скрытие карты и переход к следующему игроку."""
    game = game_manager.get_game(callback.from_user.id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    
    next_player = game.next_player()
    
    if next_player:
        await show_player_card(callback.message, state, game)
        await callback.answer("✅ Передайте телефон следующему игроку")
    else:
        # Все игроки увидели карты
        await start_game(callback.message, state, game)
        await callback.answer()


async def start_game(message, state: FSMContext, game):
    """Начинает игру."""
    await state.set_state(SpyGameStates.game_in_progress)
    game.is_active = True
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹️ Остановить игру", callback_data="stop_game")],
        [InlineKeyboardButton(text="🗳️ Голосовать", callback_data="start_voting")]
    ])
    
    # Игра начинается одинаково для всех (не показываем что все шпионы)
    text = (
        "🎮 <b>Игра началась!</b>\n\n"
        "⏱️ Таймер запущен. Обсудите и найдите шпионов!"
    )
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)
    
    # Запускаем таймер
    await start_timer(message, state, game)


async def start_timer(message, state: FSMContext, game):
    """Запускает таймер игры."""
    from app.config import settings
    from app.bot import bot
    
    duration = settings.GAME_TIMER_DURATION
    chat_id = message.chat.id
    
    timer_message = await bot.send_message(
        chat_id,
        f"⏱️ <b>Время:</b> {duration // 60}:{duration % 60:02d}"
    )
    
    game.timer_message_id = timer_message.message_id
    game.timer_chat_id = chat_id
    
    async def timer_task():
        remaining = duration
        try:
            while remaining > 0 and game.is_active:
                await asyncio.sleep(1)
                remaining -= 1
                
                minutes = remaining // 60
                seconds = remaining % 60
                
                try:
                    await bot.edit_message_text(
                        f"⏱️ <b>Время:</b> {minutes}:{seconds:02d}",
                        chat_id=game.timer_chat_id,
                        message_id=game.timer_message_id
                    )
                except:
                    pass
                
            if remaining == 0 and game.is_active:
                await bot.edit_message_text(
                    "⏰ <b>Время вышло!</b>\n\nНачните голосование.",
                    chat_id=game.timer_chat_id,
                    message_id=game.timer_message_id
                )
        except asyncio.CancelledError:
            pass
    
    game.timer_task = asyncio.create_task(timer_task())


@router.callback_query(F.data == "stop_game", StateFilter(SpyGameStates.game_in_progress))
async def handle_stop_game(callback: CallbackQuery, state: FSMContext):
    """Останавливает игру."""
    game = game_manager.get_game(callback.from_user.id)
    if game:
        game_manager.stop_game(callback.from_user.id)
    
    await state.clear()
    await callback.message.edit_text("⏹️ Игра остановлена")
    await callback.answer()


@router.callback_query(F.data == "start_voting", StateFilter(SpyGameStates.game_in_progress))
async def handle_start_voting(callback: CallbackQuery, state: FSMContext):
    """Начинает голосование."""
    game = game_manager.get_game(callback.from_user.id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    
    await state.set_state(SpyGameStates.voting)
    game.votes.clear()
    
    # Создаем клавиатуру с игроками
    buttons = []
    for i, player in enumerate(game.players):
        buttons.append([InlineKeyboardButton(
            text=f"👤 Игрок {i + 1}",
            callback_data=f"vote:{i}"
        )])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_voting")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "🗳️ <b>Голосование</b>\n\n"
        "Выберите игрока, которого считаете шпионом:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vote:"), StateFilter(SpyGameStates.voting))
async def handle_vote(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает голос."""
    game = game_manager.get_game(callback.from_user.id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    
    player_index = int(callback.data.split(":")[1])
    voted_player = game.players[player_index]
    
    # В реальной игре здесь должен быть голос конкретного игрока
    # Для упрощения считаем, что голосует создатель игры
    game.votes[callback.from_user.id] = player_index
    
    # Проверяем результат
    is_spy = voted_player.is_spy
    result_text = "✅ <b>Да, это шпион!</b>" if is_spy else "❌ <b>Нет, это не шпион.</b>"
    
    if is_spy:
        # Удаляем шпиона из игры
        game.players.remove(voted_player)
    else:
        # Удаляем обычного игрока из игры
        game.players.remove(voted_player)
    
    # Проверяем условия окончания игры
    game_result = game.check_game_end()
    
    if game_result == 'players_win':
        spies_remaining = len(game.get_spies())
        if spies_remaining == 0:
            # Все шпионы найдены
            await callback.message.edit_text(
                f"{result_text}\n\n"
                "🎉 <b>Игроки победили!</b>\n"
                "Все шпионы найдены!"
            )
        else:
            # Осталось 2 человека, среди них нет шпионов
            await callback.message.edit_text(
                f"{result_text}\n\n"
                "🎉 <b>Игроки победили!</b>\n"
                f"Осталось 2 человека, среди них нет шпионов!"
            )
        game_manager.stop_game(callback.from_user.id)
        await state.clear()
    elif game_result == 'spies_win':
        spies_remaining = len(game.get_spies())
        await callback.message.edit_text(
            f"{result_text}\n\n"
            "🕵️ <b>Шпионы победили!</b>\n"
            f"Осталось 2 человека, среди них есть шпион(ы)!"
        )
        game_manager.stop_game(callback.from_user.id)
        await state.clear()
    else:
        remaining_players = len(game.players)
        spies_remaining = len(game.get_spies())
        regular_remaining = len(game.get_regular_players())
        
        await callback.message.edit_text(
            f"{result_text}\n\n"
            f"Игра продолжается...\n"
            f"Осталось игроков: {remaining_players}\n"
            f"Шпионов: {spies_remaining}, Обычных: {regular_remaining}"
        )
        await state.set_state(SpyGameStates.game_in_progress)
    
    await callback.answer()


@router.callback_query(F.data == "cancel_game")
async def handle_cancel_game(callback: CallbackQuery, state: FSMContext):
    """Отменяет игру."""
    game = game_manager.get_game(callback.from_user.id)
    if game:
        game_manager.stop_game(callback.from_user.id)
    
    await state.clear()
    await callback.message.edit_text("❌ Игра отменена")
    await callback.answer()


@router.callback_query(F.data == "cancel_voting")
async def handle_cancel_voting(callback: CallbackQuery, state: FSMContext):
    """Отменяет голосование."""
    await state.set_state(SpyGameStates.game_in_progress)
    await callback.message.edit_text("Голосование отменено")
    await callback.answer()
