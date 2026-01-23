"""Скрипт для загрузки карт с file_id в базу данных."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ClashRoyaleCard
from app.utils.logger import logger


async def load_cards_to_database():
    """Загружает карты из JSON в базу данных."""
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    json_path = cards_dir / "cards_database.json"
    
    if not json_path.exists():
        logger.error(f"JSON файл не найден: {json_path}")
        return
    
    # Загружаем данные из JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        cards_data = json.load(f)
    
    logger.info(f"Найдено {len(cards_data)} записей для загрузки в базу данных")
    
    # Разделяем карты на обычные и эволюции
    regular_cards = {}
    evolution_cards = {}
    
    for card_data in cards_data:
        card_name = card_data['name']
        if card_name.endswith('_evolution'):
            base_name = card_name.replace('_evolution', '')
            evolution_cards[base_name] = card_data
        else:
            regular_cards[card_name] = card_data
    
    logger.info(f"Обычных карт: {len(regular_cards)}, эволюций: {len(evolution_cards)}")
    
    async for db in get_db():
        try:
            loaded_count = 0
            updated_count = 0
            
            # Обрабатываем обычные карты
            for idx, (card_name, card_data) in enumerate(regular_cards.items(), 1):
                # Проверяем, существует ли карта в базе
                result = await db.execute(
                    select(ClashRoyaleCard).where(ClashRoyaleCard.name == card_name)
                )
                existing_card = result.scalar_one_or_none()
                
                if existing_card:
                    # Обновляем существующую карту
                    existing_card.file_id = card_data.get('file_id')
                    existing_card.group = card_data.get('group', 'Unknown')
                    existing_card.elixir_cost = card_data.get('elixir_cost', 0)
                    existing_card.rarity = card_data.get('rarity', 'Common')
                    
                    # Если есть эволюция для этой карты, обновляем данные эволюции
                    if card_name in evolution_cards:
                        evo_data = evolution_cards[card_name]
                        existing_card.file_id_evolution = evo_data.get('file_id')
                        existing_card.has_evolution = True
                    else:
                        existing_card.has_evolution = False
                    
                    updated_count += 1
                    if idx % 10 == 0:
                        logger.info(f"[{idx}/{len(regular_cards)}] Обновлено карт...")
                else:
                    # Создаем новую карту
                    new_card = ClashRoyaleCard(
                        name=card_name,
                        file_id=card_data.get('file_id'),
                        has_evolution=card_name in evolution_cards,
                        group=card_data.get('group', 'Unknown'),
                        elixir_cost=card_data.get('elixir_cost', 0),
                        rarity=card_data.get('rarity', 'Common')
                    )
                    
                    # Если есть эволюция, добавляем данные эволюции
                    if card_name in evolution_cards:
                        evo_data = evolution_cards[card_name]
                        new_card.file_id_evolution = evo_data.get('file_id')
                    
                    db.add(new_card)
                    loaded_count += 1
                    if idx % 10 == 0:
                        logger.info(f"[{idx}/{len(regular_cards)}] Добавлено карт...")
            
            # Сохраняем изменения
            await db.commit()
            
            logger.info(f"✓ Загружено новых карт: {loaded_count}")
            logger.info(f"✓ Обновлено существующих карт: {updated_count}")
            logger.info(f"✓ Всего обработано: {len(regular_cards)} карт")
            
            # Удаляем JSON файл после успешной загрузки
            try:
                json_path.unlink()
                logger.info(f"✓ JSON файл удален: {json_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить JSON файл: {e}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Ошибка при загрузке карт в базу данных: {e}")
            raise


async def main():
    """Главная функция."""
    logger.info("Начинаем загрузку карт в базу данных...")
    try:
        await load_cards_to_database()
        logger.info("Загрузка в базу данных завершена успешно!")
    except KeyboardInterrupt:
        logger.warning("Загрузка прервана пользователем")
    except Exception as e:
        logger.error(f"Ошибка при загрузке: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
