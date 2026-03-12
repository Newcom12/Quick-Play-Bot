"""Скрипт для отправки картинок в бота и получения file_id."""

import asyncio
import json
import re
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

from app.config import settings
from app.database import get_db
from app.models import ClashRoyaleCard, SpyCard
from app.utils.logger import logger
from sqlalchemy import select


def normalize_name(name: str) -> str:
    """Нормализует имя для сравнения: убирает пробелы, приводит к нижнему регистру."""
    return re.sub(r'[\s_\-]+', '', name.lower())


async def upload_cards_to_bot():
    """Отправляет все картинки из папки cards в бота и получает file_id.
    Загружает только те карты, у которых еще нет file_id или file_id_evolution."""
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    
    if not cards_dir.exists():
        logger.error(f"Папка cards не найдена: {cards_dir}")
        return
    
    # Сначала проверяем, какие карты уже имеют file_id
    cards_without_file_id = []
    cards_without_evolution_file_id = []
    
    async for db in get_db():
        try:
            # Получаем все карты
            result = await db.execute(select(ClashRoyaleCard))
            all_cards = result.scalars().all()
            
            for card in all_cards:
                if not card.file_id or not card.file_id.strip():
                    cards_without_file_id.append(card.name)
                    logger.info(f"Карта {card.name} не имеет file_id")
                
                if card.has_evolution and (not card.file_id_evolution or not card.file_id_evolution.strip()):
                    cards_without_evolution_file_id.append(card.name)
                    logger.info(f"Карта {card.name} не имеет file_id_evolution")
            
            logger.info(f"Найдено карт без file_id: {len(cards_without_file_id)}")
            logger.info(f"Найдено карт без file_id_evolution: {len(cards_without_evolution_file_id)}")
        except Exception as e:
            logger.error(f"Ошибка при проверке карт в БД: {e}", exc_info=True)
        break
    
    # Находим все PNG файлы в папке cards
    png_files = list(cards_dir.glob("*.png"))
    
    if not png_files:
        logger.error(f"PNG файлы не найдены в папке: {cards_dir}")
        return
    
    logger.info(f"Найдено {len(png_files)} PNG файлов в папке")
    
    # Фильтруем файлы: загружаем только те, которые нужны
    files_to_upload = []
    
    # Создаем словари для быстрого поиска по нормализованным именам
    cards_in_db_normalized = {}  # normalized_name -> card_name
    cards_without_file_id_normalized = {}  # normalized_name -> card_name
    cards_without_evolution_file_id_normalized = {}  # normalized_name -> card_name
    
    # Сначала собираем все имена карт из БД и нормализуем их
    async for db in get_db():
        try:
            result = await db.execute(select(ClashRoyaleCard))
            all_cards = result.scalars().all()
            
            for card in all_cards:
                normalized = normalize_name(card.name)
                cards_in_db_normalized[normalized] = card.name
                
                if not card.file_id or not card.file_id.strip():
                    cards_without_file_id_normalized[normalized] = card.name
                
                if card.has_evolution and (not card.file_id_evolution or not card.file_id_evolution.strip()):
                    cards_without_evolution_file_id_normalized[normalized] = card.name
            
            logger.info(f"Карт в БД (нормализованных): {len(cards_in_db_normalized)}")
            logger.info(f"Карт без file_id (нормализованных): {len(cards_without_file_id_normalized)}")
            logger.info(f"Карт без file_id_evolution (нормализованных): {len(cards_without_evolution_file_id_normalized)}")
        except Exception as e:
            logger.error(f"Ошибка при получении списка карт из БД: {e}", exc_info=True)
        break
    
    for image_path in png_files:
        if image_path.name == "spy.png":
            # spy.png всегда обрабатываем (проверяем, нужен ли он)
            async for db in get_db():
                try:
                    result = await db.execute(select(SpyCard).where(SpyCard.name == "spy"))
                    spy_card = result.scalar_one_or_none()
                    if not spy_card or not spy_card.file_id or not spy_card.file_id.strip():
                        files_to_upload.append(image_path)
                        logger.info("Будет загружен spy.png")
                    else:
                        logger.info("spy.png уже имеет file_id, пропускаем")
                except Exception as e:
                    logger.error(f"Ошибка при проверке spy.png: {e}", exc_info=True)
                break
            continue
        
        card_name = image_path.stem  # Имя файла без расширения
        is_evolution = card_name.endswith("_evolution")
        base_name = card_name.replace("_evolution", "") if is_evolution else card_name
        
        # Нормализуем имя файла для сравнения
        normalized_base_name = normalize_name(base_name)
        
        if is_evolution:
            # Если это эволюция и карта не имеет file_id_evolution
            if normalized_base_name in cards_without_evolution_file_id_normalized:
                files_to_upload.append(image_path)
                db_card_name = cards_without_evolution_file_id_normalized[normalized_base_name]
                logger.info(f"Будет загружена эволюция: {card_name} (для карты '{db_card_name}' из БД, файл: '{base_name}')")
            else:
                logger.debug(f"Эволюция {card_name} (нормализовано: {normalized_base_name}) уже имеет file_id_evolution, пропускаем")
        else:
            # Если это обычная карта и она не имеет file_id
            if normalized_base_name in cards_without_file_id_normalized:
                files_to_upload.append(image_path)
                db_card_name = cards_without_file_id_normalized[normalized_base_name]
                logger.info(f"Будет загружена карта: {card_name} (в БД: '{db_card_name}')")
            elif normalized_base_name not in cards_in_db_normalized:
                # Карты нет в БД - тоже загружаем (она будет создана)
                files_to_upload.append(image_path)
                logger.info(f"Карта {card_name} (нормализовано: {normalized_base_name}) не найдена в БД, будет загружена и создана")
            else:
                logger.debug(f"Карта {card_name} (нормализовано: {normalized_base_name}) уже имеет file_id, пропускаем")
    
    logger.info(f"Будет загружено {len(files_to_upload)} файлов (из {len(png_files)} всего)")
    
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
        
        # Обрабатываем остальные карты (только те, которые нужны)
        for idx, image_path in enumerate(files_to_upload, 1):
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
            
            logger.info(f"[{idx}/{len(files_to_upload)}] Отправка карты: {card_name}")
            
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
                            # Ищем карту по нормализованному имени (более надежно)
                            normalized_search = normalize_name(base_name)
                            result = await db.execute(select(ClashRoyaleCard))
                            all_cards_search = result.scalars().all()
                            card = None
                            
                            # Сначала пробуем точное совпадение
                            for c in all_cards_search:
                                if c.name == base_name:
                                    card = c
                                    logger.debug(f"Найдена карта '{c.name}' по точному совпадению с '{base_name}'")
                                    break
                            
                            # Если не нашли, пробуем найти по нормализованному имени
                            if not card:
                                for c in all_cards_search:
                                    if normalize_name(c.name) == normalized_search:
                                        card = c
                                        logger.info(f"Найдена карта '{c.name}' по нормализованному имени '{base_name}' (нормализовано: {normalized_search})")
                                        break
                            
                            if card:
                                # Используем имя карты из БД для логирования
                                db_card_name = card.name
                                was_updated = False
                                
                                if is_evolution:
                                    # Обновляем file_id_evolution только если его еще нет
                                    current_evo_id = card.file_id_evolution
                                    if not current_evo_id or not current_evo_id.strip():
                                        card.file_id_evolution = file_id
                                        card.has_evolution = True
                                        was_updated = True
                                        logger.info(f"✓ Обновлен file_id_evolution для '{db_card_name}' (файл: {base_name}) в БД: {file_id[:30]}...")
                                    else:
                                        logger.warning(f"⚠ Карта '{db_card_name}' (файл: {base_name}) УЖЕ имеет file_id_evolution: {current_evo_id[:30]}...")
                                else:
                                    # Обновляем file_id только если его еще нет
                                    current_file_id = card.file_id
                                    if not current_file_id or not current_file_id.strip():
                                        card.file_id = file_id
                                        was_updated = True
                                        logger.info(f"✓ Обновлен file_id для '{db_card_name}' (файл: {base_name}) в БД: {file_id[:30]}...")
                                    else:
                                        logger.warning(f"⚠ Карта '{db_card_name}' (файл: {base_name}) УЖЕ имеет file_id: {current_file_id[:30]}...")
                                        logger.warning(f"  Это означает, что карта была обработана ранее или есть дубликат в БД")
                                        
                                # Сохраняем изменения в БД ТОЛЬКО если что-то изменилось
                                if was_updated:
                                    await db.commit()
                                    logger.debug(f"✓ Изменения сохранены в БД для '{db_card_name}'")
                                else:
                                    logger.debug(f"  Изменения не требуются для '{db_card_name}'")
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
                                logger.debug(f"✓ Новая карта сохранена в БД: {base_name}")
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
        
        logger.info(f"✓ Всего обработано {len(files_to_upload)} файлов")
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
