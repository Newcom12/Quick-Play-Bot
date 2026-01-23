"""Обработчик команды /stats."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import get_db
from app.models import PlayerStats
from app.utils.logger import logger
from sqlalchemy import select, desc

router = Router()


@router.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: CallbackQuery):
    """Обработчик кнопки статистики."""
    await cmd_stats(callback.message)
    await callback.answer()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats."""
    async for db in get_db():
        try:
            # Получаем всех игроков, отсортированных по количеству побед
            result = await db.execute(
                select(PlayerStats).order_by(desc(PlayerStats.wins), desc(PlayerStats.games_played))
            )
            all_stats = result.scalars().all()
            
            if not all_stats:
                stats_text = (
                    "📊 <b>Статистика игроков</b>\n\n"
                    "Пока нет статистики. Сыграйте несколько игр!"
                )
            else:
                stats_text = "📊 <b>Статистика игроков</b>\n\n"
                
                for i, stats in enumerate(all_stats[:20], 1):  # Показываем топ-20
                    win_rate = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
                    
                    stats_text += (
                        f"<b>{i}. {stats.player_name}</b>\n"
                        f"🎮 Игр: {stats.games_played} | "
                        f"🏆 Побед: {stats.wins} ({win_rate:.1f}%)\n"
                    )
                    
                    if stats.wins > 0:
                        win_details = []
                        if stats.wins_by_guessing > 0:
                            win_details.append(f"🕵️ Угадыванием: {stats.wins_by_guessing}")
                        if stats.wins_by_last_standing > 0:
                            win_details.append(f"👑 Последний: {stats.wins_by_last_standing}")
                        if stats.wins_by_timer > 0:
                            win_details.append(f"⏰ По таймеру: {stats.wins_by_timer}")
                        
                        if win_details:
                            stats_text += "   " + " | ".join(win_details) + "\n"
                    
                    stats_text += "\n"
                
                if len(all_stats) > 20:
                    stats_text += f"\n<i>Показано топ-20 из {len(all_stats)} игроков</i>"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_start")]
            ])
            
            await message.answer(stats_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
            await message.answer("❌ Ошибка при загрузке статистики")
        break
