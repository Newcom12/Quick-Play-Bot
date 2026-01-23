"""Скрипт для отправки картинок в бота и получения file_id."""

import asyncio
import json
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from app.config import settings
from app.database import get_db
from app.models import ClashRoyaleCard, SpyCard
from app.utils.logger import logger
from sqlalchemy import select


async def upload_cards_to_bot():
    """Отправляет все картинки из папки cards в бота и получает file_id."""
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    
    if not cards_dir.exists():
        logger.error(f"Папка cards не найдена: {cards_dir}")
        return
    
    # Находим все PNG файлы в папке cards
    png_files = list(cards_dir.glob("*.png"))
    
    if not png_files:
        logger.error(f"PNG файлы не найдены в папке: {cards_dir}")
        return
    
    logger.info(f"Найдено {len(png_files)} PNG файлов для загрузки")
    
    # Инициализируем бота
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Получаем информацию о боте, чтобы исключить его ID
    try:
        bot_info = await bot.get_me()
        bot_id = bot_info.id
        logger.info(f"ID бота: {bot_id}")
    except Exception as e:
        logger.error(f"Не удалось получить информацию о боте: {e}")
        await bot.session.close()
        return
    
    # Получаем chat_id из базы данных (ищем реального пользователя, не бота)
    chat_id = None
    
    try:
        async for db in get_db():
            from app.models import User
            # Получаем всех пользователей и ищем того, кто не является ботом
            result = await db.execute(select(User).order_by(User.id.desc()))
            all_users = result.scalars().all()
            
            for user in all_users:
                # Пропускаем, если это ID бота
                if user.telegram_id == bot_id:
                    logger.debug(f"Пропускаем пользователя {user.telegram_id} - это бот")
                    continue
                
                # Проверяем, что это не бот (проверяем через API)
                try:
                    chat = await bot.get_chat(user.telegram_id)
                    if chat.type == "private" and not chat.is_bot:
                        chat_id = user.telegram_id
                        logger.info(f"Используем chat_id пользователя: {chat_id} ({user.username or 'без username'})")
                        break
                except Exception as e:
                    logger.debug(f"Не удалось проверить пользователя {user.telegram_id}: {e}")
                    # Если не удалось проверить, но это не ID бота, используем его
                    if user.telegram_id != bot_id:
                        chat_id = user.telegram_id
                        logger.info(f"Используем chat_id пользователя (без проверки): {chat_id}")
                        break
            break
    except Exception as e:
        logger.error(f"Не удалось получить chat_id из базы: {e}")
        await bot.session.close()
        return
    
    if not chat_id:
        logger.error("⚠️  ОШИБКА: Не удалось найти реального пользователя в базе данных")
        logger.error("Отправьте боту команду /start, затем запустите скрипт снова")
        await bot.session.close()
        return
    
    if chat_id == bot_id:
        logger.error("⚠️  ОШИБКА: chat_id совпадает с ID бота. Невозможно отправить сообщение боту.")
        await bot.session.close()
        return
    
    # Список сообщений для удаления в конце
    message_ids_to_delete = []
    
    try:
        # Обрабатываем spy.png отдельно
        spy_file = cards_dir / "spy.png"
        if spy_file.exists():
            logger.info("Отправка spy.png...")
            try:
                photo = FSInputFile(spy_file)
                message = await bot.send_photo(chat_id=chat_id, photo=photo)
                message_ids_to_delete.append(message.message_id)
                
                if message.photo:
                    file_id = message.photo[-1].file_id
                    logger.info(f"✓ Получен file_id для spy.png: {file_id[:20]}...")
                    
                    # Сохраняем в БД (SpyCard)
                    async for db in get_db():
                        try:
                            result = await db.execute(
                                select(SpyCard).where(SpyCard.name == "spy")
                            )
                            spy_card = result.scalar_one_or_none()
                            
                            if spy_card:
                                spy_card.file_id = file_id
                                logger.info("✓ Обновлен file_id для spy в БД")
                            else:
                                spy_card = SpyCard(
                                    name="spy",
                                    file_id=file_id,
                                    game_name="Clash Royale",
                                    description="Карта шпиона"
                                )
                                db.add(spy_card)
                                logger.info("✓ Создана запись spy в БД")
                            
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"Ошибка при сохранении spy в БД: {e}")
                        break
                else:
                    logger.warning("✗ Не удалось получить file_id для spy.png")
                
                await asyncio.sleep(0.3)  # Небольшая задержка
            except (TelegramBadRequest, TelegramAPIError) as e:
                error_msg = str(e)
                # Если ошибка "bots can't send messages to bots", останавливаем выполнение
                if "bots can't send messages to bots" in error_msg.lower() or "forbidden" in error_msg.lower():
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {error_msg}")
                    logger.error("Останавливаем выполнение скрипта.")
                    raise
                logger.error(f"Ошибка при отправке spy.png: {e}")
                raise
            except Exception as e:
                error_msg = str(e)
                # Если ошибка "bots can't send messages to bots", останавливаем выполнение
                if "bots can't send messages to bots" in error_msg.lower() or "forbidden" in error_msg.lower():
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {error_msg}")
                    logger.error("Останавливаем выполнение скрипта.")
                    raise
                logger.error(f"Ошибка при отправке spy.png: {e}")
        
        # Обрабатываем остальные карты
        for idx, image_path in enumerate(png_files, 1):
            # Пропускаем spy.png, так как уже обработали
            if image_path.name == "spy.png":
                continue
            
            card_name = image_path.stem  # Имя файла без расширения
            
            # Обрабатываем эволюции (файлы с суффиксом _evolution)
            is_evolution = card_name.endswith("_evolution")
            if is_evolution:
                base_name = card_name.replace("_evolution", "")
            else:
                base_name = card_name
            
            logger.info(f"[{idx}/{len(png_files)}] Отправка карты: {card_name}")
            
            try:
                # Отправляем фото в бота
                photo = FSInputFile(image_path)
                message = await bot.send_photo(chat_id=chat_id, photo=photo)
                message_ids_to_delete.append(message.message_id)
                
                # Получаем file_id
                if message.photo:
                    # Берем самое большое фото (последнее в списке - самое большое)
                    file_id = message.photo[-1].file_id
                    logger.info(f"✓ Получен file_id для {card_name}: {file_id[:20]}...")
                    
                    # Сохраняем в БД
                    async for db in get_db():
                        try:
                            # Ищем карту по базовому имени
                            result = await db.execute(
                                select(ClashRoyaleCard).where(ClashRoyaleCard.name == base_name)
                            )
                            card = result.scalar_one_or_none()
                            
                            if card:
                                if is_evolution:
                                    card.file_id_evolution = file_id
                                    card.has_evolution = True
                                    logger.info(f"✓ Обновлен file_id_evolution для {base_name} в БД")
                                else:
                                    card.file_id = file_id
                                    logger.info(f"✓ Обновлен file_id для {base_name} в БД")
                            else:
                                # Создаем новую карту (если нет в БД)
                                # Пытаемся получить данные из JSON, если есть
                                json_path = cards_dir / "cards_database.json"
                                card_data = None
                                
                                if json_path.exists():
                                    try:
                                        with open(json_path, 'r', encoding='utf-8') as f:
                                            cards_data = json.load(f)
                                            # Ищем данные карты
                                            for cd in cards_data:
                                                if cd.get('name') == base_name or cd.get('name') == card_name:
                                                    card_data = cd
                                                    break
                                    except Exception as e:
                                        logger.debug(f"Не удалось загрузить JSON: {e}")
                                
                                # Создаем карту с данными из JSON или значениями по умолчанию
                                new_card = ClashRoyaleCard(
                                    name=base_name,
                                    file_id=file_id if not is_evolution else None,
                                    file_id_evolution=file_id if is_evolution else None,
                                    has_evolution=is_evolution,
                                    group=card_data.get('group', 'Unknown') if card_data else 'Unknown',
                                    elixir_cost=card_data.get('elixir_cost', 0) if card_data else 0,
                                    rarity=card_data.get('rarity', 'Common') if card_data else 'Common'
                                )
                                db.add(new_card)
                                logger.info(f"✓ Создана новая карта {base_name} в БД")
                            
                            await db.commit()
                        except Exception as e:
                            await db.rollback()
                            logger.error(f"Ошибка при сохранении {card_name} в БД: {e}")
                        break
                else:
                    logger.warning(f"✗ Не удалось получить file_id для {card_name}")
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.3)
                
            except (TelegramBadRequest, TelegramAPIError) as e:
                error_msg = str(e)
                # Если ошибка "bots can't send messages to bots", останавливаем выполнение
                if "bots can't send messages to bots" in error_msg.lower() or "forbidden" in error_msg.lower():
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {error_msg}")
                    logger.error("Останавливаем выполнение скрипта.")
                    raise
                logger.error(f"Ошибка при отправке {card_name}: {e}")
                continue
            except Exception as e:
                error_msg = str(e)
                # Если ошибка "bots can't send messages to bots", останавливаем выполнение
                if "bots can't send messages to bots" in error_msg.lower() or "forbidden" in error_msg.lower():
                    logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {error_msg}")
                    logger.error("Останавливаем выполнение скрипта.")
                    raise
                logger.error(f"Ошибка при отправке {card_name}: {e}")
                continue
        
        logger.info(f"✓ Всего обработано {len(png_files)} файлов")
        logger.info(f"✓ Сохранено {len(message_ids_to_delete)} сообщений для удаления")
        
        # Удаляем все сообщения в конце (опционально)
        logger.info("Удаление отправленных сообщений...")
        deleted_count = 0
        for msg_id in message_ids_to_delete:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted_count += 1
                await asyncio.sleep(0.1)  # Небольшая задержка между удалениями
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
        
        logger.info(f"✓ Удалено {deleted_count} из {len(message_ids_to_delete)} сообщений")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке карт: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()


async def main():
    """Главная функция."""
    logger.info("Начинаем загрузку картинок в бота...")
    try:
        await upload_cards_to_bot()
        logger.info("Загрузка завершена успешно!")
    except KeyboardInterrupt:
        logger.warning("Загрузка прервана пользователем")
    except Exception as e:
        logger.error(f"Ошибка при загрузке: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
