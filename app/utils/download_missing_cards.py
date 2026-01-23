"""Скрипт для доскачивания недостающих карт."""

import asyncio
import re
from pathlib import Path

import aiohttp
from PIL import Image

from app.config import settings
from app.utils.logger import logger

# Карты, которые не удалось скачать
MISSING_CARDS = [
    "Goblinstein Monk",
    "Empress"
]

# Специальные случаи для URL
SPECIAL_URLS = {
    "Goblinstein Monk": [
        "https://www.deckshop.pro/img/card_ed/Goblinstein.png",
        "https://www.deckshop.pro/img/card_ed/Monk.png",
        "https://royaleapi.com/static/img/cards-150/goblinstein-monk.png",
        "https://cdn.royaleapi.com/static/img/cards-150/goblinstein-monk.png",
        "https://www.deckshop.pro/img/cards/goblinstein-monk.png",
    ],
    "Empress": [
        "https://www.deckshop.pro/img/card_ed/SpiritEmpress.png",
        "https://www.deckshop.pro/img/card_ed/Empress.png",
        "https://royaleapi.com/static/img/cards-150/empress.png",
        "https://cdn.royaleapi.com/static/img/cards-150/empress.png",
        "https://www.deckshop.pro/img/cards/empress.png",
        "https://royaleapi.com/static/img/cards-150/spirit-empress.png",
        "https://cdn.royaleapi.com/static/img/cards-150/spirit-empress.png",
    ]
}


async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path) -> bool:
    """Скачивает изображение по URL и сохраняет его."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                content = await response.read()
                
                # Проверяем, что это действительно изображение
                if len(content) < 100:
                    logger.debug(f"Файл слишком маленький для {url}: {len(content)} байт")
                    return False
                
                with open(save_path, 'wb') as f:
                    f.write(content)
                
                # Проверяем и конвертируем в PNG если нужно
                try:
                    img = Image.open(save_path)
                    if img.format != 'PNG':
                        if img.mode in ('RGBA', 'LA'):
                            img.save(save_path.with_suffix('.png'), 'PNG')
                        else:
                            img_rgba = img.convert('RGBA')
                            img_rgba.save(save_path.with_suffix('.png'), 'PNG')
                        save_path.unlink()
                        save_path = save_path.with_suffix('.png')
                    logger.info(f"✓ Изображение сохранено: {save_path.name}")
                    return True
                except Exception as e:
                    logger.debug(f"Ошибка обработки изображения {save_path}: {e}")
                    if save_path.exists():
                        save_path.unlink()
                    return False
            elif response.status == 404:
                return False
            else:
                logger.debug(f"Ошибка скачивания {url}: статус {response.status}")
                return False
    except asyncio.CancelledError:
        raise
    except aiohttp.ClientError as e:
        logger.debug(f"Ошибка сети при скачивании {url}: {e}")
        return False
    except Exception as e:
        logger.debug(f"Ошибка при скачивании {url}: {e}")
        return False


async def download_missing_cards():
    """Скачивает недостающие карты."""
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        for card_name in MISSING_CARDS:
            logger.info(f"Попытка скачать: {card_name}")
            
            # Нормализуем имя файла
            safe_name = re.sub(r'[^\w\s-]', '', card_name).strip().replace(' ', '_')
            image_path = cards_dir / f"{safe_name}.png"
            
            # Пропускаем, если уже скачано
            if image_path.exists():
                logger.info(f"✓ {card_name} уже существует: {image_path.name}")
                continue
            
            # Получаем список URL для попытки
            urls = SPECIAL_URLS.get(card_name, [])
            
            # Добавляем стандартные URL
            card_slug = card_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
            card_slug = re.sub(r'[^\w-]', '', card_slug)
            urls.extend([
                f"https://royaleapi.com/static/img/cards-150/{card_slug}.png",
                f"https://cdn.royaleapi.com/static/img/cards-150/{card_slug}.png",
                f"https://www.deckshop.pro/img/cards/{card_slug}.png",
                f"https://royaleapi.com/static/img/cards/{card_slug}.png",
                f"https://cdn.royaleapi.com/static/img/cards/{card_slug}.png",
            ])
            
            # Пробуем все URL
            downloaded = False
            for url in urls:
                if not url:
                    continue
                logger.debug(f"Пробуем: {url}")
                if await download_image(session, url, image_path):
                    downloaded = True
                    break
                await asyncio.sleep(0.2)
            
            if not downloaded:
                logger.warning(f"✗ Не удалось скачать {card_name}")
            else:
                logger.info(f"✓ {card_name} успешно скачан")
            
            await asyncio.sleep(0.5)
    
    logger.info("Доскачивание завершено!")


async def main():
    """Главная функция."""
    logger.info("Начинаем доскачивание недостающих карт...")
    try:
        await download_missing_cards()
    except KeyboardInterrupt:
        logger.warning("Доскачивание прервано пользователем")
    except Exception as e:
        logger.error(f"Ошибка при доскачивании: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
