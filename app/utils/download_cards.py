"""Скрипт для скачивания карт Clash Royale."""

import asyncio

from app.utils.card_parser import download_all_cards
from app.utils.logger import logger


async def main():
    """Главная функция для скачивания карт."""
    logger.info("Начинаем скачивание карт Clash Royale...")
    
    try:
        result = await download_all_cards()
        logger.info(f"Скачивание завершено успешно!")
        logger.info(f"JSON база данных: {result['json_path']}")
        logger.info(f"Всего карт: {len(result['cards'])}")
    except KeyboardInterrupt:
        logger.warning("Скачивание прервано пользователем")
        logger.info("Частично скачанные данные сохранены")
    except asyncio.CancelledError:
        logger.warning("Скачивание отменено")
    except Exception as e:
        logger.error(f"Ошибка при скачивании карт: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
