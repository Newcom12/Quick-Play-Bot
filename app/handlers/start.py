"""Обработчик команды /start."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.utils.logger import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start с красивым HTML форматированием."""
    user = message.from_user
    db: Session = next(SessionLocal())

    try:
        # Проверка существования пользователя в БД
        db_user = db.query(User).filter(User.telegram_id == user.id).first()

        if not db_user:
            # Создание нового пользователя
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Новый пользователь зарегистрирован: {user.id} (@{user.username})")
        else:
            # Обновление информации о пользователе
            db_user.username = user.username
            db_user.first_name = user.first_name
            db_user.last_name = user.last_name
            db.commit()
            logger.info(f"Информация о пользователе обновлена: {user.id}")

        # Красивое приветственное сообщение с HTML форматированием
        welcome_text = f"""
<b>👋 Добро пожаловать, {user.first_name}!</b>

<i>Я QuickPlayBot - ваш помощник для быстрой игры!</i>

<b>✨ Возможности:</b>
• 🎮 Быстрый старт игр
• 📊 Статистика ваших игр
• 🏆 Достижения и рекорды
• ⚙️ Настройки профиля

<b>📝 Доступные команды:</b>
/start - Начать работу с ботом
/help - Получить помощь

<b>🚀 Готовы начать?</b>
Используйте команды выше или просто отправьте сообщение!

<i>Приятного использования! 🎉</i>
        """.strip()

        await message.answer(welcome_text)

    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке команды. Попробуйте позже."
        )
    finally:
        db.close()
