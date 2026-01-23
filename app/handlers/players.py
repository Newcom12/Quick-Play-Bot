"""Обработчик управления игроками."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import get_db
from app.models import SavedPlayer
from app.utils.logger import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()


class PlayerManagementStates(StatesGroup):
    """Состояния управления игроками."""
    waiting_for_player_name = State()


@router.callback_query(F.data == "manage_players")
async def manage_players_callback(callback: CallbackQuery):
    """Обработчик кнопки управления игроками."""
    await cmd_players(callback.message)
    await callback.answer()


@router.message(Command("players"))
async def cmd_players(message: Message):
    """Обработчик команды /players - управление игроками."""
    user_id = message.from_user.id
    
    async for db in get_db():
        try:
            result = await db.execute(
                select(SavedPlayer).where(SavedPlayer.user_id == user_id).order_by(SavedPlayer.created_at)
            )
            players = result.scalars().all()
            
            if not players:
                text = (
                    "👥 <b>Управление игроками</b>\n\n"
                    "У вас пока нет сохраненных игроков.\n"
                    "Добавьте первого игрока!"
                )
            else:
                text = "👥 <b>Управление игроками</b>\n\n"
                text += "<b>Сохраненные игроки:</b>\n"
                for i, player in enumerate(players, 1):
                    text += f"{i}. {player.name}\n"
            
            buttons = [
                [InlineKeyboardButton(text="➕ Добавить игрока", callback_data="add_saved_player")],
            ]
            
            if players:
                buttons.append([InlineKeyboardButton(text="➖ Удалить игрока", callback_data="remove_saved_player")])
            
            buttons.append([InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_start")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer(text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при получении игроков: {e}", exc_info=True)
            await message.answer("❌ Ошибка при загрузке списка игроков")
        break


@router.callback_query(F.data == "add_saved_player")
async def add_saved_player_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления игрока."""
    await state.set_state(PlayerManagementStates.waiting_for_player_name)
    await callback.message.edit_text(
        "➕ <b>Добавление игрока</b>\n\n"
        "Введите имя игрока:"
    )
    await callback.answer()


@router.message(F.text, StateFilter(PlayerManagementStates.waiting_for_player_name))
async def handle_player_name_input(message: Message, state: FSMContext):
    """Обрабатывает ввод имени игрока."""
    player_name = message.text.strip()
    
    if not player_name or len(player_name) > 50:
        await message.answer("❌ Имя должно быть от 1 до 50 символов. Попробуйте снова:")
        return
    
    user_id = message.from_user.id
    
    async for db in get_db():
        try:
            # Проверяем, нет ли уже такого игрока
            result = await db.execute(
                select(SavedPlayer).where(
                    SavedPlayer.user_id == user_id,
                    SavedPlayer.name == player_name
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                await message.answer(f"❌ Игрок с именем '{player_name}' уже существует.")
                await state.clear()
                await cmd_players(message)
                return
            
            # Создаем нового игрока
            new_player = SavedPlayer(
                user_id=user_id,
                name=player_name
            )
            db.add(new_player)
            await db.commit()
            
            logger.info(f"Добавлен игрок {player_name} для пользователя {user_id}")
            await message.answer(f"✅ Игрок '{player_name}' успешно добавлен!")
            await state.clear()
            await cmd_players(message)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Ошибка при добавлении игрока: {e}", exc_info=True)
            await message.answer("❌ Ошибка при добавлении игрока")
        break


@router.callback_query(F.data == "remove_saved_player")
async def remove_saved_player_callback(callback: CallbackQuery):
    """Обработчик удаления игрока."""
    user_id = callback.from_user.id
    
    async for db in get_db():
        try:
            result = await db.execute(
                select(SavedPlayer).where(SavedPlayer.user_id == user_id).order_by(SavedPlayer.created_at)
            )
            players = result.scalars().all()
            
            if not players:
                await callback.answer("Нет игроков для удаления", show_alert=True)
                return
            
            buttons = []
            for player in players:
                buttons.append([InlineKeyboardButton(
                    text=f"❌ {player.name}",
                    callback_data=f"delete_player:{player.id}"
                )])
            
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_players_menu")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                "➖ <b>Удаление игрока</b>\n\n"
                "Выберите игрока для удаления:",
                reply_markup=keyboard
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка при получении игроков: {e}", exc_info=True)
            await callback.answer("❌ Ошибка", show_alert=True)
        break


@router.callback_query(F.data.startswith("delete_player:"))
async def delete_player_confirm(callback: CallbackQuery):
    """Подтверждает удаление игрока."""
    player_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    async for db in get_db():
        try:
            # Проверяем, что игрок принадлежит пользователю
            result = await db.execute(
                select(SavedPlayer).where(
                    SavedPlayer.id == player_id,
                    SavedPlayer.user_id == user_id
                )
            )
            player = result.scalar_one_or_none()
            
            if not player:
                await callback.answer("Игрок не найден", show_alert=True)
                return
            
            player_name = player.name
            await db.execute(
                delete(SavedPlayer).where(SavedPlayer.id == player_id)
            )
            await db.commit()
            
            logger.info(f"Удален игрок {player_name} для пользователя {user_id}")
            await callback.answer(f"✅ Игрок '{player_name}' удален")
            await cmd_players(callback.message)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Ошибка при удалении игрока: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при удалении", show_alert=True)
        break


@router.callback_query(F.data == "back_to_players_menu")
async def back_to_players_menu(callback: CallbackQuery):
    """Возврат к меню управления игроками."""
    await cmd_players(callback.message)
    await callback.answer()
