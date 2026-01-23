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


@router.callback_query(F.data.startswith("game:"), StateFilter(SpyGameStates.waiting_for_game_selection))
async def handle_game_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор игры."""
    game_type = callback.data.split(":")[1]
    
    await state.update_data(game_type=game_type)
    await state.set_state(SpyGameStates.waiting_for_evolution_setting)
    
    # Клавиатура настройки эволюций
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Использовать эволюции", callback_data="evolution:true")],
        [InlineKeyboardButton(text="❌ Не использовать эволюции", callback_data="evolution:false")],
        [InlineKeyboardButton(text="🎲 Случайно", callback_data="evolution:random")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")]
    ])
    
    game_name = "Clash Royale" if game_type == "clash_royale" else game_type
    
    await callback.message.edit_text(
        f"🎮 <b>Игра: {game_name}</b>\n\n"
        "🔄 Использовать эволюции карт?\n\n"
        "Если включено, карты с эволюциями будут показываться в двух вариантах.",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("evolution:"), StateFilter(SpyGameStates.waiting_for_evolution_setting))
async def handle_evolution_setting(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает настройку использования эволюций."""
    evolution_setting = callback.data.split(":")[1]
    
    if evolution_setting == "random":
        import random
        use_evolutions = random.choice([True, False])
        setting_text = f"🎲 Случайно: {'✅ Использовать' if use_evolutions else '❌ Не использовать'}"
    elif evolution_setting == "true":
        use_evolutions = True
        setting_text = "✅ Использовать эволюции"
    else:
        use_evolutions = False
        setting_text = "❌ Не использовать эволюции"
    
    await state.update_data(use_evolutions=use_evolutions)
    await state.set_state(SpyGameStates.waiting_for_players_count)
    
    keyboard = create_number_keyboard(3, 10, "players_count")
    
    await callback.message.edit_text(
        f"🎮 <b>Игра Шпион</b>\n\n"
        f"🔄 Эволюции: {setting_text}\n\n"
        "👥 Выберите количество игроков:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(Command("spy"))
async def cmd_spy(message: Message, state: FSMContext):
    """Команда для начала игры Шпион."""
    game_id = str(uuid.uuid4())[:8]
    game = game_manager.create_game(message.from_user.id, game_id)
    
    await state.update_data(game_id=game_id)
    await state.set_state(SpyGameStates.waiting_for_game_selection)
    
    # Клавиатура выбора игры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Clash Royale", callback_data="game:clash_royale")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")]
    ])
    
    await message.answer(
        "🎮 <b>Игра Шпион</b>\n\n"
        "🎯 Выберите игру:",
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
    
    # Переходим к управлению игроками
    await state.set_state(SpyGameStates.managing_players)
    await state.update_data(players_list=[])  # Список игроков с именами
    
    # Показываем меню управления игроками
    await show_players_management(callback.message, state, players_count)
    await callback.answer()


async def show_players_management(message, state: FSMContext, players_count: int):
    """Показывает меню управления игроками."""
    data = await state.get_data()
    players_list = data.get("players_list", [])
    
    text = f"👥 <b>Управление игроками</b>\n\n"
    text += f"✅ Игроков добавлено: <b>{len(players_list)}/{players_count}</b>\n\n"
    
    if players_list:
        text += "<b>Список игроков:</b>\n"
        for i, player in enumerate(players_list, 1):
            text += f"{i}. {player['name']}\n"
    else:
        text += "Пока нет игроков. Добавьте первого игрока!"
    
    buttons = []
    if len(players_list) < players_count:
        buttons.append([InlineKeyboardButton(text="➕ Добавить игрока", callback_data="add_player")])
    
    if players_list:
        buttons.append([InlineKeyboardButton(text="➖ Удалить игрока", callback_data="remove_player")])
        if len(players_list) == players_count:
            buttons.append([InlineKeyboardButton(text="✅ Начать игру", callback_data="start_game_setup")])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_game")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "add_player", StateFilter(SpyGameStates.managing_players))
async def handle_add_player(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает добавление игрока."""
    data = await state.get_data()
    players_count = data.get("players_count")
    players_list = data.get("players_list", [])
    
    if len(players_list) >= players_count:
        await callback.answer("Достигнуто максимальное количество игроков", show_alert=True)
        return
    
    await state.set_state(SpyGameStates.waiting_for_player_name)
    await callback.message.edit_text(
        f"👤 <b>Добавление игрока {len(players_list) + 1}</b>\n\n"
        "Введите имя игрока:"
    )
    await callback.answer()


@router.message(StateFilter(SpyGameStates.waiting_for_player_name))
async def handle_player_name_input(message: Message, state: FSMContext):
    """Обрабатывает ввод имени игрока."""
    player_name = message.text.strip()
    
    if not player_name or len(player_name) > 50:
        await message.answer("❌ Имя должно быть от 1 до 50 символов. Попробуйте снова:")
        return
    
    data = await state.get_data()
    players_list = data.get("players_list", [])
    players_count = data.get("players_count")
    
    # Проверяем на дубликаты
    if any(p['name'].lower() == player_name.lower() for p in players_list):
        await message.answer("❌ Игрок с таким именем уже добавлен. Введите другое имя:")
        return
    
    # Добавляем игрока
    players_list.append({"name": player_name, "index": len(players_list)})
    await state.update_data(players_list=players_list)
    await state.set_state(SpyGameStates.managing_players)
    
    # Показываем обновленное меню
    await show_players_management(message, state, players_count)


@router.callback_query(F.data == "remove_player", StateFilter(SpyGameStates.managing_players))
async def handle_remove_player(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает удаление игрока."""
    data = await state.get_data()
    players_list = data.get("players_list", [])
    
    if not players_list:
        await callback.answer("Нет игроков для удаления", show_alert=True)
        return
    
    # Создаем клавиатуру с игроками для удаления
    buttons = []
    for i, player in enumerate(players_list):
        buttons.append([InlineKeyboardButton(
            text=f"❌ {player['name']}",
            callback_data=f"remove_player:{i}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_players")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "➖ <b>Удаление игрока</b>\n\n"
        "Выберите игрока для удаления:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_player:"), StateFilter(SpyGameStates.managing_players))
async def handle_remove_player_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждает удаление игрока."""
    player_index = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    players_list = data.get("players_list", [])
    players_count = data.get("players_count")
    
    if 0 <= player_index < len(players_list):
        removed_player = players_list.pop(player_index)
        # Обновляем индексы
        for i, player in enumerate(players_list):
            player['index'] = i
        await state.update_data(players_list=players_list)
        await callback.answer(f"✅ Игрок {removed_player['name']} удален")
    
    await show_players_management(callback.message, state, players_count)


@router.callback_query(F.data == "back_to_players", StateFilter(SpyGameStates.managing_players))
async def handle_back_to_players(callback: CallbackQuery, state: FSMContext):
    """Возвращает к меню управления игроками."""
    data = await state.get_data()
    players_count = data.get("players_count")
    await show_players_management(callback.message, state, players_count)
    await callback.answer()


@router.callback_query(F.data == "start_game_setup", StateFilter(SpyGameStates.managing_players))
async def handle_start_game_setup(callback: CallbackQuery, state: FSMContext):
    """Начинает настройку игры после добавления всех игроков."""
    data = await state.get_data()
    players_list = data.get("players_list", [])
    players_count = data.get("players_count")
    spies_count = data.get("spies_count")
    
    if len(players_list) != players_count:
        await callback.answer("Добавьте всех игроков перед началом игры", show_alert=True)
        return
    
    # Получаем настройки игры
    data = await state.get_data()
    game_type = data.get("game_type", "clash_royale")
    use_evolutions = data.get("use_evolutions", False)
    
    # Загружаем карты из базы данных
    cards_list = []
    async for db in get_db():
        try:
            if game_type == "clash_royale":
                result = await db.execute(select(ClashRoyaleCard))
                all_cards = result.scalars().all()
                
                logger.info(f"Всего карт в БД: {len(all_cards)}")
                
                cards_list = [
                    {
                        "name": card.name,
                        "file_id": card.file_id,
                        "file_id_evolution": card.file_id_evolution,
                        "has_evolution": card.has_evolution
                    }
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
        players_list,
        spies_count,
        cards_list,
        use_evolutions=use_evolutions
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
    
    current_player = game.get_current_player()
    player_name = current_player.username if current_player else f"Игрок {game.current_player_index + 1}"
    
    text = (
        f"👤 <b>{player_name}</b>\n\n"
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
        # Обычный игрок видит карту
        if current_player.has_evolution and current_player.file_id_evolution:
            # Карта с эволюцией - отправляем обе картинки
            text = (
                f"🎴 <b>Ваша карта:</b> {current_player.card_name}\n\n"
                "✨ <b>У этой карты есть эволюция!</b>\n\n"
                "Ниже показаны оба варианта:"
            )
            await callback.message.edit_text(text, reply_markup=keyboard)
            
            # Отправляем обычную версию
            if current_player.file_id:
                await callback.message.answer_photo(
                    current_player.file_id,
                    caption=f"🎴 {current_player.card_name} (Обычная версия)"
                )
            
            # Отправляем эволюцию
            await callback.message.answer_photo(
                current_player.file_id_evolution,
                caption=f"✨ {current_player.card_name} (Эволюция)"
            )
        else:
            # Обычная карта без эволюции
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
        [InlineKeyboardButton(text="🕵️ Угадать тему", callback_data="guess_theme")],
        [InlineKeyboardButton(text="🗳️ Голосовать", callback_data="start_voting")],
        [InlineKeyboardButton(text="⏹️ Остановить игру", callback_data="stop_game")]
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
                game.timer_expired = True
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
    
    # Если таймер истек, определяем победителей
    if game.timer_expired:
        await handle_timer_end(callback.message, state, game)
        await callback.answer()
        return
    
    await state.set_state(SpyGameStates.voting)
    game.votes.clear()
    
    # Создаем клавиатуру с игроками
    buttons = []
    for i, player in enumerate(game.players):
        buttons.append([InlineKeyboardButton(
            text=f"👤 {player.username}",
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


async def handle_timer_end(message, state: FSMContext, game):
    """Обрабатывает окончание игры по таймеру."""
    spies = game.get_spies()
    regular = game.get_regular_players()
    
    spies_count = len(spies)
    regular_count = len(regular)
    
    # Если есть шпионы - они побеждают (таймер истек, они не были найдены)
    if spies_count > 0:
        text = (
            "⏰ <b>Время вышло!</b>\n\n"
            "🕵️ <b>Шпионы победили!</b>\n"
            f"Осталось шпионов: {spies_count}\n"
            f"Осталось обычных игроков: {regular_count}"
        )
        
        # Сохраняем статистику
        for player in spies:
            await save_player_stats(player.username, win=True, win_type="timer")
        for player in regular:
            await save_player_stats(player.username, win=False)
    else:
        # Все шпионы найдены - обычные игроки побеждают
        text = (
            "⏰ <b>Время вышло!</b>\n\n"
            "🎉 <b>Игроки победили!</b>\n"
            "Все шпионы были найдены до истечения времени!"
        )
        
        # Сохраняем статистику
        for player in regular:
            await save_player_stats(player.username, win=True, win_type="timer")
    
    await message.answer(text)
    game_manager.stop_game(message.from_user.id)
    await state.clear()


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
    
    # Сохраняем статистику для выбывшего игрока
    await save_player_stats(voted_player.username, win=False)
    
    # Удаляем игрока из игры
    game.players.remove(voted_player)
    
    # Проверяем условия окончания игры
    game_result = game.check_game_end()
    
    if game_result == 'players_win':
        spies_remaining = len(game.get_spies())
        if spies_remaining == 0:
            # Все шпионы найдены
            # Сохраняем статистику
            for player in game.players:
                if not player.is_spy:
                    await save_player_stats(player.username, win=True, win_type="last_standing")
            for spy in game.get_spies():
                await save_player_stats(spy.username, win=False)
            
            await callback.message.edit_text(
                f"{result_text}\n\n"
                "🎉 <b>Игроки победили!</b>\n"
                "Все шпионы найдены!"
            )
        else:
            # Осталось 2 человека, среди них нет шпионов
            # Сохраняем статистику
            for player in game.players:
                if not player.is_spy:
                    await save_player_stats(player.username, win=True, win_type="last_standing")
            
            await callback.message.edit_text(
                f"{result_text}\n\n"
                "🎉 <b>Игроки победили!</b>\n"
                f"Осталось 2 человека, среди них нет шпионов!"
            )
        game_manager.stop_game(callback.from_user.id)
        await state.clear()
    elif game_result == 'spies_win':
        spies_remaining = len(game.get_spies())
        # Сохраняем статистику
        for player in game.players:
            if player.is_spy:
                await save_player_stats(player.username, win=True, win_type="last_standing")
            else:
                await save_player_stats(player.username, win=False)
        
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


@router.callback_query(F.data == "guess_theme", StateFilter(SpyGameStates.game_in_progress))
async def handle_guess_theme(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает попытку угадать тему игры."""
    game = game_manager.get_game(callback.from_user.id)
    if not game:
        await callback.answer("Игра не найдена", show_alert=True)
        return
    
    # Проверяем, является ли текущий игрок шпионом
    current_player = None
    for player in game.players:
        if player.user_id == callback.from_user.id and player.is_spy:
            current_player = player
            break
    
    if not current_player:
        await callback.answer("Только шпионы могут угадывать тему игры", show_alert=True)
        return
    
    await state.set_state(SpyGameStates.waiting_for_guess)
    await callback.message.edit_text(
        f"🕵️ <b>Угадывание темы</b>\n\n"
        f"Игрок: <b>{current_player.username}</b>\n\n"
        "Введите название карты (тему игры):"
    )
    await callback.answer()


@router.message(StateFilter(SpyGameStates.waiting_for_guess))
async def handle_guess_input(message: Message, state: FSMContext):
    """Обрабатывает ввод угадывания темы."""
    guessed_theme = message.text.strip()
    
    if not guessed_theme:
        await message.answer("❌ Введите название карты. Попробуйте снова:")
        return
    
    game = game_manager.get_game(message.from_user.id)
    if not game:
        await state.clear()
        await message.answer("❌ Игра не найдена")
        return
    
    # Проверяем угадывание
    is_correct, winner_name = game_manager.check_guess(message.from_user.id, guessed_theme)
    
    # Находим игрока-шпиона
    guessing_player = None
    for player in game.players:
        if player.user_id == message.from_user.id and player.is_spy:
            guessing_player = player
            break
    
    if not guessing_player:
        await state.set_state(SpyGameStates.game_in_progress)
        await message.answer("❌ Ошибка: вы не являетесь шпионом")
        return
    
    if is_correct:
        # Шпион угадал - он выигрывает, игра заканчивается
        game.is_active = False
        if game.timer_task:
            game.timer_task.cancel()
        
        # Сохраняем статистику
        await save_player_stats(guessing_player.username, win=True, win_type="guessing")
        
        # Удаляем всех остальных игроков из статистики (поражение)
        for player in game.players:
            if player.username != guessing_player.username:
                await save_player_stats(player.username, win=False)
        
        await message.answer(
            f"🎉 <b>ПОБЕДА!</b>\n\n"
            f"🕵️ <b>{guessing_player.username}</b> угадал тему игры!\n\n"
            f"✅ Тема игры: <b>{game.game_theme}</b>\n\n"
            f"Игра окончена."
        )
        
        game_manager.stop_game(message.from_user.id)
        await state.clear()
    else:
        # Шпион не угадал - он выбывает
        game.players.remove(guessing_player)
        
        # Сохраняем статистику
        await save_player_stats(guessing_player.username, win=False)
        
        # Проверяем условия окончания игры
        game_result = game.check_game_end()
        
        if game_result == 'players_win':
            # Все шпионы найдены или осталось 2 человека без шпионов
            spies_remaining = len(game.get_spies())
            if spies_remaining == 0:
                text = (
                    f"❌ <b>{guessing_player.username}</b> не угадал тему игры и выбывает.\n\n"
                    "🎉 <b>Игроки победили!</b>\n"
                    "Все шпионы найдены!"
                )
            else:
                text = (
                    f"❌ <b>{guessing_player.username}</b> не угадал тему игры и выбывает.\n\n"
                    "🎉 <b>Игроки победили!</b>\n"
                    "Осталось 2 человека, среди них нет шпионов!"
                )
            
            # Сохраняем статистику победителей
            for player in game.players:
                if not player.is_spy:
                    await save_player_stats(player.username, win=True, win_type="last_standing")
            
            await message.answer(text)
            game_manager.stop_game(message.from_user.id)
            await state.clear()
        elif game_result == 'spies_win':
            # Осталось 2 человека, среди них есть шпион
            text = (
                f"❌ <b>{guessing_player.username}</b> не угадал тему игры и выбывает.\n\n"
                "🕵️ <b>Шпионы победили!</b>\n"
                "Осталось 2 человека, среди них есть шпион(ы)!"
            )
            
            # Сохраняем статистику победителей
            for player in game.players:
                if player.is_spy:
                    await save_player_stats(player.username, win=True, win_type="last_standing")
            
            await message.answer(text)
            game_manager.stop_game(message.from_user.id)
            await state.clear()
        else:
            # Игра продолжается
            remaining_players = len(game.players)
            spies_remaining = len(game.get_spies())
            regular_remaining = len(game.get_regular_players())
            
            await message.answer(
                f"❌ <b>{guessing_player.username}</b> не угадал тему игры и выбывает.\n\n"
                f"Игра продолжается...\n"
                f"Осталось игроков: {remaining_players}\n"
                f"Шпионов: {spies_remaining}, Обычных: {regular_remaining}"
            )
            await state.set_state(SpyGameStates.game_in_progress)


async def save_player_stats(player_name: str, win: bool, win_type: str = None):
    """Сохраняет статистику игрока."""
    from app.models import PlayerStats
    
    async for db in get_db():
        try:
            result = await db.execute(
                select(PlayerStats).where(PlayerStats.player_name == player_name)
            )
            stats = result.scalar_one_or_none()
            
            if not stats:
                stats = PlayerStats(player_name=player_name)
                db.add(stats)
            
            stats.games_played += 1
            
            if win:
                stats.wins += 1
                if win_type == "guessing":
                    stats.wins_by_guessing += 1
                elif win_type == "last_standing":
                    stats.wins_by_last_standing += 1
                elif win_type == "timer":
                    stats.wins_by_timer += 1
            else:
                stats.losses += 1
            
            await db.commit()
            logger.info(f"Статистика обновлена для {player_name}: побед={stats.wins}, игр={stats.games_played}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении статистики для {player_name}: {e}", exc_info=True)
            await db.rollback()
        break
