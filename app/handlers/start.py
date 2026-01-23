"""Обработчик команды /start."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot import bot
from app.config import settings
from app.database import get_db
from app.models import User
from app.utils.logger import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    """Проверяет подписку после нажатия кнопки."""
    if not settings.CHANNEL_ID:
        await callback.answer("Канал не настроен", show_alert=True)
        return
    
    try:
        chat_member = await bot.get_chat_member(settings.CHANNEL_ID, callback.from_user.id)
        if chat_member.status in ['left', 'kicked']:
            await callback.answer("❌ Вы еще не подписались на канал", show_alert=True)
            return
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки: {e}")
        await callback.answer("Ошибка при проверке подписки", show_alert=True)
        return
    
    # Если подписан, показываем главное меню
    await cmd_start(callback.message)
    await callback.answer("✅ Отлично!")


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    user = message.from_user
    
    logger.info(f"Пользователь {user.id} ({user.username}) использовал команду /start")
    
    # Проверка подписки на канал
    if settings.CHANNEL_ID:
        try:
            chat_member = await bot.get_chat_member(settings.CHANNEL_ID, user.id)
            if chat_member.status in ['left', 'kicked']:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{settings.CHANNEL_ID.replace('@', '')}")],
                    [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
                ])
                await message.answer(
                    f"❌ Для использования бота необходимо подписаться на канал:\n"
                    f"👉 {settings.CHANNEL_ID}\n\n"
                    f"После подписки нажмите кнопку ниже.",
                    reply_markup=keyboard
                )
                return
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки: {e}")
            # Продолжаем работу в случае ошибки
    
    async for db in get_db():
        try:
            # Проверяем, существует ли пользователь
            result = await db.execute(
                select(User).where(User.telegram_id == user.id)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Обновляем информацию о пользователе
                existing_user.username = user.username
                existing_user.first_name = user.first_name
                existing_user.last_name = user.last_name
                existing_user.is_active = True
                logger.info(f"Обновлена информация о пользователе {user.id}")
            else:
                # Создаем нового пользователя
                new_user = User(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_active=True,
                )
                db.add(new_user)
                logger.info(f"Создан новый пользователь {user.id}")
            
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Ошибка при работе с базой данных: {e}")
            raise
        break
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть в Шпиона", callback_data="start_spy_game")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="show_help")]
    ])
    
    welcome_message = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        "🎮 Добро пожаловать в <b>QuickPlayBot</b>!\n\n"
        "Выберите действие:"
    )
    
    await message.answer(welcome_message, reply_markup=keyboard)
