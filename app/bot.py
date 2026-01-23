"""Инициализация бота и роутера."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, KeyboardButton, ReplyKeyboardMarkup

from app.config import settings
from app.utils.logger import logger

# Инициализация бота
bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# Инициализация диспетчера
dp = Dispatcher()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает постоянную клавиатуру главного меню."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Играть в Шпиона")],
            [KeyboardButton(text="📖 Правила"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard


async def set_bot_commands():
    """Регистрация команд бота через set_my_commands."""
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="help", description="ℹ️ Получить помощь"),
        BotCommand(command="spy", description="🎮 Играть в Шпиона"),
        BotCommand(command="rules", description="📖 Правила игры"),
        BotCommand(command="stats", description="📊 Статистика игроков"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота успешно зарегистрированы")


async def on_startup():
    """Действия при запуске бота."""
    logger.info("Бот запускается...")
    await set_bot_commands()
    logger.info("Бот успешно запущен")


async def on_shutdown():
    """Действия при остановке бота."""
    logger.info("Бот останавливается...")
    await bot.session.close()
    logger.info("Бот успешно остановлен")
