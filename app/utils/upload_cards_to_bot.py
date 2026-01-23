"""Скрипт для отправки картинок в бота и получения file_id."""

import asyncio
import json
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import settings
from app.utils.logger import logger


async def upload_cards_to_bot():
    """Отправляет все картинки в бота и получает file_id."""
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    json_path = cards_dir / "cards_database.json"
    
    # Загружаем данные из JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        cards_data = json.load(f)
    
    logger.info(f"Найдено {len(cards_data)} карт для загрузки")
    
    # Инициализируем бота
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Получаем chat_id из базы данных (последний пользователь) или из обновлений
    chat_id = None
    
    # Пробуем получить chat_id из базы данных (последний пользователь)
    try:
        from app.database import get_db
        from app.models import User
        from sqlalchemy import select
        
        async for db in get_db():
            result = await db.execute(select(User).order_by(User.id.desc()).limit(1))
            last_user = result.scalar_one_or_none()
            if last_user:
                chat_id = last_user.telegram_id
                logger.info(f"Используем chat_id из базы данных: {chat_id}")
            break
    except Exception as e:
        logger.debug(f"Не удалось получить chat_id из базы: {e}")
    
    # Если не нашли в базе, пробуем получить из обновлений
    if not chat_id:
        try:
            updates = await bot.get_updates(limit=10, timeout=1)
            for update in updates:
                if update.message:
                    chat_id = update.message.chat.id
                    logger.info(f"Найден chat_id из обновлений: {chat_id}")
                    break
        except Exception as e:
            logger.debug(f"Не удалось получить chat_id из обновлений: {e}")
    
    if not chat_id:
        me = await bot.get_me()
        logger.error(f"Бот: @{me.username}")
        logger.error("⚠️  ОШИБКА: Не удалось определить chat_id")
        logger.error("Отправьте боту команду /start, затем запустите скрипт снова")
        await bot.session.close()
        return
    
    # Словарь для хранения file_id
    file_ids_map = {}
    
    try:
        for idx, card in enumerate(cards_data, 1):
            card_name = card['name']
            image_path_str = card.get('image_path', '')
            
            # Преобразуем путь в абсолютный
            if image_path_str.startswith('app/'):
                image_path = project_root / image_path_str.replace('\\', '/')
            else:
                image_path = Path(image_path_str)
            
            if not image_path.exists():
                logger.warning(f"Файл не найден: {image_path} для карты {card_name}")
                continue
            
            logger.info(f"[{idx}/{len(cards_data)}] Отправка карты: {card_name}")
            
            try:
                # Отправляем фото в бота
                photo = FSInputFile(image_path)
                message = await bot.send_photo(chat_id=chat_id, photo=photo)
                
                # Получаем file_id
                if message.photo:
                    # Берем самое большое фото (последнее в списке - самое большое)
                    file_id = message.photo[-1].file_id
                    file_ids_map[card_name] = file_id
                    logger.info(f"✓ Получен file_id для {card_name}: {file_id[:20]}...")
                else:
                    logger.warning(f"✗ Не удалось получить file_id для {card_name}")
                
                # Удаляем сообщение
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                except:
                    pass
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при отправке {card_name}: {e}")
                continue
        
        # Сохраняем file_id в JSON
        for card in cards_data:
            card_name = card['name']
            if card_name in file_ids_map:
                card['file_id'] = file_ids_map[card_name]
        
        # Сохраняем обновленный JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ File_id сохранены для {len(file_ids_map)} карт")
        logger.info(f"Обновленный JSON сохранен: {json_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке карт: {e}")
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
