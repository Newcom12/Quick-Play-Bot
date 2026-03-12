"""Утилита для парсинга и скачивания карт Clash Royale."""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from PIL import Image

from app.config import settings
from app.utils.logger import logger

# Список карт с эволюцией (39 штук)
EVOLUTION_CARDS = [
    "Skeletons", "Ice Spirit", "Bomber", "Bats", "Zap", "Giant Snowball",
    "Archers", "Knight", "Cannon", "Skeleton Barrel", "Firecracker", "Mortar",
    "Tesla", "Barbarians", "Royal Giant", "Royal Recruits", "Dart Goblin",
    "Musketeer", "Goblin Cage", "Valkyrie", "Battle Ram", "Furnace", "Wizard",
    "Royal Hogs", "Wall Breakers", "Goblin Barrel", "Skeleton Army", "Baby Dragon",
    "Hunter", "Goblin Drill", "Witch", "Electro Dragon", "Executioner", "Goblin Giant",
    "P.E.K.K.A", "Royal Ghost", "Inferno Dragon", "Lumberjack", "Mega Knight"
]

# Группы карт
CARD_GROUPS = {
    "With evolutions": EVOLUTION_CARDS,  # Группа для всех карт с эволюцией
    "Spells": ["Zap", "Giant Snowball", "Arrows", "Royal Delivery", "Earthquake", "Fireball", 
               "Rocket", "Mirror", "Barbarian Barrel", "Goblin Curse", "Rage", "Goblin Barrel",
               "Vines", "Clone", "Tornado", "Void", "Freeze", "Poison", "Lightning", "The Log", "Graveyard"],
    "Melee": ["Skeletons", "Goblins", "Berserker", "Goblin Gang", "Barbarians", "Rascals",
              "Elixir Golem", "Mini P.E.K.K.A", "Goblin Cage", "Barbarian Barrel", "Goblin Barrel",
              "Skeleton Army", "Giant Skeleton", "Bandit", "Lumberjack", "Graveyard", "Boss Bandit",
              "Bats", "Knight", "Elite Barbarians", "Valkyrie", "Dark Prince", "Rune Giant",
              "Goblin Giant", "P.E.K.K.A", "Electro Giant", "Miner", "Royal Ghost", "Fisherman",
              "Goblin Machine", "Spirit Empress", "Empress", "Mega Knight", "Golden Knight", "Skeleton King",
              "Goblinstein Monk", "Minions", "Royal Delivery", "Minion Horde", "Royal Recruits",
              "Mega Minion", "Battle Healer", "Guards", "Prince", "Phoenix", "Night Witch", "Mighty Miner"],
    "Melee": ["Skeletons", "Goblins", "Berserker", "Goblin Gang", "Barbarians", "Rascals",
              "Elixir Golem", "Mini P.E.K.K.A", "Goblin Cage", "Barbarian Barrel", "Goblin Barrel",
              "Skeleton Army", "Giant Skeleton", "Bandit", "Lumberjack", "Graveyard", "Boss Bandit",
              "Bats", "Knight", "Elite Barbarians", "Valkyrie", "Dark Prince", "Rune Giant",
              "Goblin Giant", "P.E.K.K.A", "Electro Giant", "Miner", "Royal Ghost", "Fisherman",
              "Goblin Machine", "Spirit Empress", "Empress", "Mega Knight", "Golden Knight", "Skeleton King",
              "Goblinstein Monk", "Minions", "Royal Delivery", "Minion Horde", "Royal Recruits",
              "Mega Minion", "Battle Healer", "Guards", "Prince", "Phoenix", "Night Witch", "Mighty Miner"],
    "Ranged": ["Spear Goblins", "Bomber", "Archers", "Cannon", "Goblin Gang", "Firecracker",
               "Skeleton Dragons", "Rascals", "Dart Goblin", "Musketeer", "Goblin Hut", "Flying Machine",
               "Furnace", "Zappies", "Goblin Demolisher", "Wizard", "Three Musketeers", "Baby Dragon",
               "Hunter", "Witch", "Electro Dragon", "Bowler", "Executioner", "Cannon Cart", "Goblin Giant",
               "X-Bow", "Princess", "Ice Wizard", "Fisherman", "Electro Wizard", "Inferno Dragon",
               "Magic Archer", "Mother Witch", "Ram Rider", "Sparky", "Spirit Empress", "Empress", "Little Prince",
               "Archer Queen", "Goblinstein"],
    "Buildings": ["Cannon", "Mortar", "Tesla", "Tombstone", "Goblin Cage", "Goblin Hut",
                  "Bomb Tower", "Inferno Tower", "Barbarian Hut", "Elixir Collector", "Goblin Drill", "X-Bow"],
    "Air units": ["Bats", "Minions", "Skeleton Barrel", "Skeleton Dragons", "Minion Horde",
                  "Mega Minion", "Flying Machine", "Baby Dragon", "Balloon", "Electro Dragon",
                  "Inferno Dragon", "Phoenix", "Spirit Empress", "Empress", "Lava Hound"],
    "Ground units": ["Skeletons", "Electro Spirit", "Fire Spirit", "Ice Spirit", "Goblins",
                     "Spear Goblins", "Bomber", "Berserker", "Archers", "Knight", "Goblin Gang",
                     "Firecracker", "Royal Delivery", "Barbarians", "Rascals", "Royal Giant",
                     "Elite Barbarians", "Royal Recruits", "Heal Spirit", "Ice Golem", "Suspicious Bush",
                     "Dart Goblin", "Elixir Golem", "Mini P.E.K.K.A", "Musketeer", "Goblin Cage",
                     "Valkyrie", "Battle Ram", "Hog Rider", "Battle Healer", "Furnace", "Zappies",
                     "Goblin Demolisher", "Giant", "Wizard", "Royal Hogs", "Three Musketeers",
                     "Barbarian Barrel", "Wall Breakers", "Goblin Barrel", "Guards", "Skeleton Army",
                     "Dark Prince", "Rune Giant", "Hunter", "Witch", "Prince", "Bowler", "Executioner",
                     "Cannon Cart", "Giant Skeleton", "Goblin Giant", "P.E.K.K.A", "Electro Giant",
                     "Golem", "Miner", "Princess", "Ice Wizard", "Royal Ghost", "Bandit", "Fisherman",
                     "Electro Wizard", "Magic Archer", "Lumberjack", "Night Witch", "Mother Witch",
                     "Ram Rider", "Goblin Machine", "Sparky", "Spirit Empress", "Empress", "Mega Knight",
                     "Little Prince", "Golden Knight", "Skeleton King", "Mighty Miner", "Archer Queen",
                     "Goblinstein Monk", "Boss Bandit"]
}


async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path) -> bool:
    """Скачивает изображение по URL и сохраняет его."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                content = await response.read()
                
                # Проверяем, что это действительно изображение
                if len(content) < 100:  # Слишком маленький файл - вероятно, не изображение
                    logger.debug(f"Файл слишком маленький для {url}: {len(content)} байт")
                    return False
                
                with open(save_path, 'wb') as f:
                    f.write(content)
                
                # Проверяем и конвертируем в PNG если нужно
                try:
                    img = Image.open(save_path)
                    if img.format != 'PNG':
                        # Конвертируем в PNG
                        if img.mode in ('RGBA', 'LA'):
                            img.save(save_path.with_suffix('.png'), 'PNG')
                        else:
                            # Создаем с альфа-каналом
                            img_rgba = img.convert('RGBA')
                            img_rgba.save(save_path.with_suffix('.png'), 'PNG')
                        save_path.unlink()  # Удаляем старый файл
                        save_path = save_path.with_suffix('.png')
                    logger.debug(f"Изображение сохранено: {save_path.name}")
                    return True
                except Exception as e:
                    logger.debug(f"Ошибка обработки изображения {save_path}: {e}")
                    # Удаляем поврежденный файл
                    if save_path.exists():
                        save_path.unlink()
                    return False
            elif response.status == 404:
                # 404 - нормально, просто файла нет
                return False
            else:
                logger.debug(f"Ошибка скачивания {url}: статус {response.status}")
                return False
    except asyncio.CancelledError:
        # Прерывание операции
        raise
    except aiohttp.ClientError as e:
        logger.debug(f"Ошибка сети при скачивании {url}: {e}")
        return False
    except Exception as e:
        logger.debug(f"Ошибка при скачивании {url}: {e}")
        return False


def get_card_group(card_name: str, is_evolution: bool = False) -> str:
    """Определяет группу карты по её названию."""
    # Если это эволюция, возвращаем специальную группу
    if is_evolution:
        return "With evolutions"
    
    # Ищем группу для обычной карты (исключая группу "With evolutions")
    for group, cards in CARD_GROUPS.items():
        if group == "With evolutions":
            continue
        if card_name in cards:
            return group
    return "Unknown"


def get_card_elixir_cost(card_name: str) -> int:
    """Определяет стоимость карты в эликсире (из данных сайта)."""
    # Данные из сайта deckshop.pro
    elixir_map = {
        # 1 эликсир
        "Skeletons": 1, "Electro Spirit": 1, "Fire Spirit": 1, "Ice Spirit": 1, "Heal Spirit": 1,
        # 2 эликсир
        "Goblins": 2, "Spear Goblins": 2, "Bomber": 2, "Bats": 2, "Zap": 2, "Giant Snowball": 2,
        "Berserker": 2, "Ice Golem": 2, "Suspicious Bush": 2, "Barbarian Barrel": 2, "Wall Breakers": 2,
        "Goblin Curse": 2, "Rage": 2, "The Log": 2, "Mirror": 2,
        # 3 эликсир
        "Archers": 3, "Arrows": 3, "Knight": 3, "Minions": 3, "Cannon": 3, "Goblin Gang": 3,
        "Skeleton Barrel": 3, "Firecracker": 3, "Royal Delivery": 3, "Tombstone": 3, "Mega Minion": 3,
        "Dart Goblin": 3, "Earthquake": 3, "Elixir Golem": 3, "Goblin Barrel": 3, "Guards": 3,
        "Skeleton Army": 3, "Vines": 3, "Clone": 3, "Tornado": 3, "Void": 3, "Miner": 3, "Princess": 3,
        "Ice Wizard": 3, "Royal Ghost": 3, "Bandit": 3, "Fisherman": 3, "Little Prince": 3,
        # 4 эликсир
        "Skeleton Dragons": 4, "Mortar": 4, "Tesla": 4, "Fireball": 4, "Mini P.E.K.K.A": 4,
        "Musketeer": 4, "Goblin Cage": 4, "Goblin Hut": 4, "Valkyrie": 4, "Battle Ram": 4,
        "Bomb Tower": 4, "Flying Machine": 4, "Hog Rider": 4, "Battle Healer": 4, "Furnace": 4,
        "Zappies": 4, "Goblin Demolisher": 4, "Baby Dragon": 4, "Dark Prince": 4, "Freeze": 4,
        "Poison": 4, "Rune Giant": 4, "Hunter": 4, "Goblin Drill": 4, "Electro Wizard": 4,
        "Inferno Dragon": 4, "Phoenix": 4, "Magic Archer": 4, "Lumberjack": 4, "Night Witch": 4,
        "Mother Witch": 4, "Golden Knight": 4, "Skeleton King": 4, "Mighty Miner": 4,
        # 5 эликсир
        "Barbarians": 5, "Minion Horde": 5, "Rascals": 5, "Giant": 5, "Inferno Tower": 5,
        "Wizard": 5, "Royal Hogs": 5, "Witch": 5, "Balloon": 5, "Prince": 5, "Electro Dragon": 5,
        "Bowler": 5, "Executioner": 5, "Cannon Cart": 5, "Ram Rider": 5, "Graveyard": 5,
        "Goblin Machine": 5, "Archer Queen": 5, "Goblinstein Monk": 5,
        # 6 эликсир
        "Royal Giant": 6, "Elite Barbarians": 6, "Rocket": 6, "Barbarian Hut": 6, "Elixir Collector": 6,
        "Giant Skeleton": 6, "Lightning": 6, "Goblin Giant": 6, "X-Bow": 6, "Sparky": 6,
        "Spirit Empress": 6, "Empress": 6, "Boss Bandit": 6,
        # 7 эликсир
        "Royal Recruits": 7, "P.E.K.K.A": 7, "Electro Giant": 7, "Mega Knight": 7, "Lava Hound": 7,
        # 8 эликсир
        "Golem": 8,
        # 9 эликсир
        "Three Musketeers": 9,
    }
    return elixir_map.get(card_name, 0)


def get_card_rarity(card_name: str) -> str:
    """Определяет редкость карты."""
    # Данные из сайта
    champion = ["Little Prince", "Golden Knight", "Skeleton King", "Mighty Miner", "Archer Queen", 
                "Goblinstein Monk", "Boss Bandit"]
    legendary = ["The Log", "Miner", "Princess", "Ice Wizard", "Royal Ghost", "Bandit", "Fisherman",
                 "Electro Wizard", "Inferno Dragon", "Phoenix", "Magic Archer", "Lumberjack",
                 "Night Witch", "Mother Witch", "Ram Rider", "Graveyard", "Goblin Machine", "Sparky",
                 "Spirit Empress", "Empress", "Mega Knight", "Lava Hound"]
    epic = ["Mirror", "Barbarian Barrel", "Wall Breakers", "Goblin Curse", "Rage", "Goblin Barrel",
            "Guards", "Skeleton Army", "Vines", "Clone", "Tornado", "Void", "Baby Dragon", "Dark Prince",
            "Freeze", "Poison", "Rune Giant", "Hunter", "Goblin Drill", "Witch", "Balloon", "Prince",
            "Electro Dragon", "Bowler", "Executioner", "Cannon Cart", "Giant Skeleton", "Lightning",
            "Goblin Giant", "X-Bow", "P.E.K.K.A", "Electro Giant", "Golem"]
    rare = ["Heal Spirit", "Ice Golem", "Suspicious Bush", "Tombstone", "Mega Minion", "Dart Goblin",
            "Earthquake", "Elixir Golem", "Fireball", "Mini P.E.K.K.A", "Musketeer", "Goblin Cage",
            "Goblin Hut", "Valkyrie", "Battle Ram", "Bomb Tower", "Flying Machine", "Hog Rider",
            "Battle Healer", "Furnace", "Zappies", "Goblin Demolisher", "Giant", "Inferno Tower",
            "Wizard", "Royal Hogs", "Rocket", "Barbarian Hut", "Elixir Collector", "Three Musketeers"]
    
    if card_name in champion:
        return "Champion"
    elif card_name in legendary:
        return "Legendary"
    elif card_name in epic:
        return "Epic"
    elif card_name in rare:
        return "Rare"
    else:
        return "Common"


def get_card_image_url(card_name: str, evolution: bool = False) -> Optional[str]:
    """Генерирует URL изображения карты на основе известных паттернов."""
    # Нормализуем имя карты для URL
    card_slug = card_name.lower().replace(' ', '-').replace('.', '').replace("'", '').replace('p.e.k.k.a', 'pekka')
    card_slug = re.sub(r'[^\w-]', '', card_slug)
    
    # Специальные случаи для некоторых карт
    special_cases = {
        'the-log': 'the-log',
        'mini-p-e-k-k-a': 'mini-pekka',
        'mini-pekka': 'mini-pekka',
        'p-e-k-k-a': 'pekka',
        'pekka': 'pekka',
        'x-bow': 'x-bow',
        'xbow': 'x-bow',
        'three-musketeers': 'three-musketeers',
        'goblinstein-monk': 'goblinstein-monk',
        'goblinsteinmonk': 'goblinstein-monk',
        'boss-bandit': 'boss-bandit',
        'bossbandit': 'boss-bandit',
        'spirit-empress': 'spirit-empress',
        'spiritempress': 'spirit-empress',
        'empress': 'empress',
    }
    if card_slug in special_cases:
        card_slug = special_cases[card_slug]
    
    # Базовый URL для изображений Clash Royale
    # Используем несколько возможных источников
    if evolution:
        base_urls = [
            f"https://royaleapi.com/static/img/cards-150/{card_slug}-evolution.png",
            f"https://cdn.royaleapi.com/static/img/cards-150/{card_slug}-evolution.png",
            f"https://www.deckshop.pro/img/cards/{card_slug}-evolution.png",
            f"https://royaleapi.com/static/img/cards/{card_slug}-evolution.png",
            f"https://cdn.royaleapi.com/static/img/cards/{card_slug}-evolution.png",
            # Альтернативные форматы
            f"https://royaleapi.com/static/img/cards-150/{card_slug}_evolution.png",
            f"https://cdn.royaleapi.com/static/img/cards-150/{card_slug}_evolution.png",
        ]
    else:
        base_urls = [
            f"https://royaleapi.com/static/img/cards-150/{card_slug}.png",
            f"https://cdn.royaleapi.com/static/img/cards-150/{card_slug}.png",
            f"https://www.deckshop.pro/img/cards/{card_slug}.png",
            f"https://royaleapi.com/static/img/cards/{card_slug}.png",
            f"https://cdn.royaleapi.com/static/img/cards/{card_slug}.png",
        ]
    
    return base_urls[0] if base_urls else None


async def parse_deckshop_site() -> List[Dict]:
    """Парсит сайт deckshop.pro и извлекает информацию о картах."""
    url = "https://www.deckshop.pro/card/list"
    cards_data = []
    
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Сначала парсим секцию "With evolutions" для получения URL эволюций
                    evolution_section = soup.find('h3', string=re.compile(r'With evolutions', re.I))
                    evolution_cards_map = {}  # Имя карты -> ссылка на изображение эволюции
                    
                    if evolution_section:
                        evolution_container = evolution_section.find_next_sibling()
                        if evolution_container:
                            evolution_links = evolution_container.find_all('a', href=re.compile(r'/card/.*evolution', re.I))
                            for evo_link in evolution_links:
                                img = evo_link.find('img')
                                if img:
                                    img_src = img.get('src') or img.get('data-src') or ''
                                    # Извлекаем имя карты из URL
                                    href = evo_link.get('href', '')
                                    card_match = re.search(r'/card/detail/([^?]+)', href)
                                    if card_match:
                                        card_slug = card_match.group(1)
                                        # Преобразуем slug в имя карты
                                        card_name = card_slug.replace('-', ' ').title()
                                        # Специальные случаи
                                        if card_slug == 'pekka':
                                            card_name = 'P.E.K.K.A'
                                        elif card_slug == 'mini-pekka':
                                            card_name = 'Mini P.E.K.K.A'
                                        elif card_slug == 'x-bow':
                                            card_name = 'X-Bow'
                                        elif card_slug == '3m' or card_slug == 'three-musketeers':
                                            card_name = 'Three Musketeers'
                                        
                                        if img_src:
                                            evolution_cards_map[card_name] = urljoin(url, img_src)
                    
                    # Ищем все ссылки на карты (исключая эволюции)
                    card_links = soup.find_all('a', href=re.compile(r'/card/detail/', re.I))
                    
                    # Фильтруем эволюции
                    card_links = [link for link in card_links if 'evolution=1' not in link.get('href', '')]
                    
                    logger.info(f"Найдено {len(card_links)} ссылок на карты")
                    logger.info(f"Найдено {len(evolution_cards_map)} эволюций")
                    
                    # Извлекаем названия карт из ссылок
                    for link in card_links:
                        # Получаем имя карты из URL
                        href = link.get('href', '')
                        card_match = re.search(r'/card/detail/([^?]+)', href)
                        if not card_match:
                            continue
                        
                        card_slug = card_match.group(1)
                        # Преобразуем slug в имя карты
                        card_name = card_slug.replace('-', ' ').title()
                        
                        # Специальные случаи для имен карт
                        special_names = {
                            'pekka': 'P.E.K.K.A',
                            'mini-pekka': 'Mini P.E.K.K.A',
                            'x-bow': 'X-Bow',
                            '3m': 'Three Musketeers',
                            'three-musketeers': 'Three Musketeers',
                            'the-log': 'The Log',
                            'rg': 'Royal Giant',
                            'e-barbs': 'Elite Barbarians',
                            'mp': 'Mini P.E.K.K.A',
                            'mm': 'Mega Minion',
                            'e-wiz': 'Electro Wizard',
                            'e-dragon': 'Electro Dragon',
                            'inferno-d': 'Inferno Dragon',
                            'baby-d': 'Baby Dragon',
                            'gob-giant': 'Goblin Giant',
                            'gob-cage': 'Goblin Cage',
                            'gob-hut': 'Goblin Hut',
                            'gob-gang': 'Goblin Gang',
                            'gob-drill': 'Goblin Drill',
                            'gob-demolisher': 'Goblin Demolisher',
                            'gob-machine': 'Goblin Machine',
                            'goblinstein': 'Goblinstein',
                            'monk': 'Monk',
                            'spirit-empress': 'Spirit Empress',
                            'boss-bandit': 'Boss Bandit',
                        }
                        
                        if card_slug in special_names:
                            card_name = special_names[card_slug]
                        
                        # Если не нашли имя из URL, пробуем из текста или alt
                        if not card_name or len(card_name) < 2:
                            card_name = link.get_text(strip=True)
                            if not card_name:
                                img = link.find('img')
                                if img:
                                    card_name = img.get('alt') or img.get('title') or ''
                        
                        # Фильтруем не-карты
                        if not card_name or len(card_name) < 2:
                            continue
                        
                        # Список исключений для навигационных элементов
                        excluded_keywords = [
                            'cambiar', 'переключить', 'switch', 'hide', 'skip ad', 'tell me more',
                            'changer', 'wechseln', 'cambia', 'zmień', 'değiştir', 'trocar', 'verander',
                            'غير', '切换到中文', 'přepnout', 'prepnúť', 'byt', 'cards', 'english', 'español',
                            'русский', 'français', 'deutsch', 'italiano', 'polski', 'türkçe', 'português',
                            'nederlands', 'العربية', '中文', 'česky', 'slovensky', 'svenska', 'list',
                            'by arena', 'damage', 'hitpoints', 'other stats', 'for nerds', 'help translate',
                            'deck spy', 'deck builder', 'deck check', 'best decks', 'merge tactics',
                            'deck finder', 'cards', 'guides', 'about', 'discord bot', 'languages',
                            'support', 'buy', 'store', 'bonus', 'points', 'offer', 'pass', 'royale'
                        ]
                        
                        card_name_lower = card_name.lower()
                        if any(keyword in card_name_lower for keyword in excluded_keywords):
                            continue
                        
                        # Исключаем элементы с эмодзи флагов
                        flag_emojis = ['🇺🇸', '🇪🇸', '🇷🇺', '🇫🇷', '🇩🇪', '🇮🇹', '🇵🇱', '🇹🇷', '🇧🇷', '🇳🇱', '🇦🇪', '🇨🇳', '🇨🇿', '🇸🇰', '🇸🇪']
                        if any(flag in card_name for flag in flag_emojis):
                            continue
                        
                        # Пропускаем дубликаты
                        if card_name in [c.get('name') for c in cards_data]:
                            continue
                        
                        card_link = link.get('href', '')
                        card_url = urljoin(url, card_link) if card_link else None
                        
                        # Ищем изображение
                        img_elem = link.find('img')
                        img_url = None
                        if img_elem:
                            img_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                            if img_url:
                                img_url = urljoin(url, img_url)
                        
                        # Если не нашли, генерируем URL
                        if not img_url:
                            img_url = get_card_image_url(card_name, False)
                        
                        # Получаем URL эволюции из карты эволюций
                        evolution_img_url = evolution_cards_map.get(card_name)
                        
                        has_evolution = card_name in EVOLUTION_CARDS
                        group = get_card_group(card_name)
                        elixir = get_card_elixir_cost(card_name)
                        rarity = get_card_rarity(card_name)
                        
                        cards_data.append({
                            'name': card_name,
                            'image_url': img_url,
                            'evolution_image_url': evolution_img_url,
                            'card_url': card_url,
                            'has_evolution': has_evolution,
                            'group': group,
                            'elixir_cost': elixir,
                            'rarity': rarity
                        })
                    
                    logger.info(f"Извлечено {len(cards_data)} карт")
                    return cards_data
                else:
                    logger.error(f"Ошибка при загрузке страницы: статус {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка при парсинге сайта: {e}")
            return []


async def download_all_cards() -> Dict:
    """Скачивает все карты и создает JSON базу данных."""
    # Используем абсолютный путь от корня проекта
    project_root = Path(__file__).parent.parent.parent
    cards_dir = project_root / "app" / "data" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    
    # Используем предопределенный список карт (более надежно)
    logger.info("Используем предопределенный список карт")
    cards_data = create_cards_from_web_data()
    
    # Пытаемся дополнить URL изображений из парсинга сайта
    parsed_cards = await parse_deckshop_site()
    if parsed_cards:
        # Создаем словарь для быстрого поиска URL
        parsed_urls = {card['name']: card.get('image_url') for card in parsed_cards if card.get('image_url')}
        # Обновляем URL для карт, которые нашли на сайте
        for card in cards_data:
            if card['name'] in parsed_urls:
                card['image_url'] = parsed_urls[card['name']]
    
    json_db = []
    
    async with aiohttp.ClientSession() as session:
        total_cards = len(cards_data)
        for idx, card_info in enumerate(cards_data, 1):
            try:
                card_name = card_info['name']
                has_evolution = card_info['has_evolution']
                
                logger.info(f"Обработка карты {idx}/{total_cards}: {card_name}")
                
                # Нормализуем имя файла
                safe_name = re.sub(r'[^\w\s-]', '', card_name).strip().replace(' ', '_')
                
                # Путь для обычной карты
                image_path = cards_dir / f"{safe_name}.png"
                
                # Пропускаем скачивание, если файл уже существует
                if not image_path.exists():
                    # Скачиваем обычную карту - пробуем несколько URL
                    image_urls = [
                        card_info.get('image_url'),
                        get_card_image_url(card_name, False),
                    ]
                    
                    # Добавляем альтернативные URL если основной не найден
                    if not any(image_urls):
                        card_slug = card_name.lower().replace(' ', '-').replace('.', '').replace("'", '').replace('p.e.k.k.a', 'pekka')
                        card_slug = re.sub(r'[^\w-]', '', card_slug)
                        
                        # Применяем специальные случаи
                        special_cases = {
                            'the-log': 'the-log',
                            'mini-pekka': 'mini-pekka',
                            'pekka': 'pekka',
                            'x-bow': 'x-bow',
                            'three-musketeers': 'three-musketeers',
                            'goblinstein-monk': 'goblinstein-monk',
                            'goblinsteinmonk': 'goblinstein-monk',
                            'boss-bandit': 'boss-bandit',
                            'bossbandit': 'boss-bandit',
                            'spirit-empress': 'spirit-empress',
                            'spiritempress': 'spirit-empress',
                            'empress': 'empress',
                        }
                        if card_slug in special_cases:
                            card_slug = special_cases[card_slug]
                        
                        image_urls.extend([
                            f"https://royaleapi.com/static/img/cards-150/{card_slug}.png",
                            f"https://cdn.royaleapi.com/static/img/cards-150/{card_slug}.png",
                            f"https://www.deckshop.pro/img/cards/{card_slug}.png",
                            f"https://royaleapi.com/static/img/cards/{card_slug}.png",
                            f"https://cdn.royaleapi.com/static/img/cards/{card_slug}.png",
                        ])
                    
                    # Пробуем все URL по очереди
                    downloaded = False
                    for image_url in image_urls:
                        if not image_url:
                            continue
                        if await download_image(session, image_url, image_path):
                            downloaded = True
                            break
                    
                    if not downloaded and not image_path.exists():
                        logger.warning(f"Не удалось скачать изображение для {card_name}")
                    
                    # Небольшая задержка между запросами
                    await asyncio.sleep(0.1)
                
                # Для карт с эволюцией скачиваем также вариант с эволюцией
                evolution_path = None
                if has_evolution:
                    evolution_path = cards_dir / f"{safe_name}_evolution.png"
                    
                    # Пропускаем, если файл уже существует
                    if not evolution_path.exists():
                        # Нормализуем имя для URL эволюции
                        evolution_slug = card_name.lower().replace(' ', '-').replace('.', '').replace("'", '').replace('p.e.k.k.a', 'pekka')
                        evolution_slug = re.sub(r'[^\w-]', '', evolution_slug)
                        
                        # Специальные случаи для эволюций
                        evolution_special = {
                            'the-log': 'the-log',
                            'mini-pekka': 'mini-pekka',
                            'pekka': 'pekka',
                            'x-bow': 'x-bow',
                            'three-musketeers': 'three-musketeers',
                            'goblinstein-monk': 'goblinstein-monk',
                            'boss-bandit': 'boss-bandit',
                            'spirit-empress': 'spirit-empress',
                            'empress': 'empress',
                        }
                        if evolution_slug in evolution_special:
                            evolution_slug = evolution_special[evolution_slug]
                        
                        # Пытаемся найти URL для эволюции
                        # Используем URL из парсинга секции "With evolutions"
                        evolution_url = card_info.get('evolution_image_url')
                        
                        # Если URL эволюции найден при парсинге, используем его напрямую
                        if evolution_url:
                            logger.debug(f"Используем найденный URL эволюции для {card_name}: {evolution_url}")
                            if await download_image(session, evolution_url, evolution_path):
                                logger.info(f"✓ Эволюция для {card_name} скачана: {evolution_path.name}")
                            else:
                                logger.warning(f"✗ Не удалось скачать эволюцию для {card_name} с найденного URL")
                        # Если не нашли через парсинг, пробуем стандартные URL
                        else:
                            # Создаем разные варианты slug для поиска
                            evolution_slug_variants = [
                                evolution_slug,
                                safe_name.lower().replace('_', '-'),
                                card_name.lower().replace(' ', '-'),
                                card_name.lower().replace(' ', '-').replace('.', '').replace("'", ''),
                            ]
                            
                            evolution_urls = [
                                get_card_image_url(card_name, evolution=True),
                            ]
                            
                            # Добавляем URL для каждого варианта slug
                            # Также пробуем URL из deckshop.pro с путем card_ed_evo (как на странице)
                            evolution_file_names = {
                                'skeletons': 'Skellies',
                                'ice-spirit': 'IceSpirit',
                                'bomber': 'Bomber',
                                'bats': 'Bats',
                                'zap': 'Zap',
                                'giant-snowball': 'Snowball',
                                'archers': 'Archers',
                                'knight': 'Knight',
                                'cannon': 'Cannon',
                                'skeleton-barrel': 'SkellyBarrel',
                                'firecracker': 'Firecracker',
                                'mortar': 'Mortar',
                                'tesla': 'Tesla',
                                'barbarians': 'Barbs',
                                'royal-giant': 'RG',
                                'royal-recruits': 'RoyalRecruits',
                                'dart-goblin': 'DartGob',
                                'musketeer': 'Musk',
                                'goblin-cage': 'GoblinCage',
                                'valkyrie': 'Valk',
                                'battle-ram': 'Ram',
                                'furnace': 'Furnace',
                                'wizard': 'Wiz',
                                'royal-hogs': 'RoyalHogs',
                                'wall-breakers': 'WallBreakers',
                                'goblin-barrel': 'Barrel',
                                'skeleton-army': 'Skarmy',
                                'baby-dragon': 'BabyD',
                                'hunter': 'Hunter',
                                'goblin-drill': 'GoblinDrill',
                                'witch': 'Witch',
                                'electro-dragon': 'eDragon',
                                'executioner': 'Exe',
                                'goblin-giant': 'GobGiant',
                                'pekka': 'PEKKA',
                                'royal-ghost': 'Ghost',
                                'inferno-dragon': 'InfernoD',
                                'lumberjack': 'Lumber',
                                'mega-knight': 'MegaKnight',
                            }
                            
                            for slug_var in evolution_slug_variants:
                                # Пробуем стандартные URL
                                evolution_urls.extend([
                                    f"https://royaleapi.com/static/img/cards-150/{slug_var}-evolution.png",
                                    f"https://cdn.royaleapi.com/static/img/cards-150/{slug_var}-evolution.png",
                                    f"https://www.deckshop.pro/img/cards/{slug_var}-evolution.png",
                                    f"https://royaleapi.com/static/img/cards/{slug_var}-evolution.png",
                                    f"https://cdn.royaleapi.com/static/img/cards/{slug_var}-evolution.png",
                                    # Альтернативные форматы
                                    f"https://royaleapi.com/static/img/cards-150/{slug_var}_evolution.png",
                                    f"https://cdn.royaleapi.com/static/img/cards-150/{slug_var}_evolution.png",
                                ])
                                
                                # Пробуем URL из deckshop.pro с путем card_ed_evo
                                if slug_var in evolution_file_names:
                                    evo_file_name = evolution_file_names[slug_var]
                                    evolution_urls.append(f"https://www.deckshop.pro/img/card_ed_evo/{evo_file_name}.png")
                            
                            # Пробуем все URL по очереди
                            downloaded = False
                            for url in evolution_urls:
                                if not url:
                                    continue
                                logger.debug(f"Пробуем скачать эволюцию {card_name} с {url}")
                                if await download_image(session, url, evolution_path):
                                    downloaded = True
                                    logger.info(f"✓ Эволюция для {card_name} скачана: {evolution_path.name}")
                                    break
                            
                            if not downloaded and not evolution_path.exists():
                                logger.warning(f"✗ Не удалось скачать эволюцию для {card_name}")
                        
                        await asyncio.sleep(0.1)
                # Добавляем в JSON базу
                # Используем относительный путь от корня проекта
                try:
                    rel_image_path = str(image_path.relative_to(project_root))
                except ValueError:
                    # Если путь не в подпапке, используем абсолютный путь
                    rel_image_path = str(image_path)
                
                if has_evolution:
                    # Для карт с эволюцией создаем ДВЕ отдельные записи
                    
                    # 1. Обычная версия (без эволюции) - в обычной группе
                    card_entry_normal = {
                        'name': card_name,
                        'image_path': rel_image_path,
                        'has_evolution': False,  # Обычная версия без эволюции
                        'group': card_info['group'],  # Обычная группа (Melee, Ranged и т.д.)
                        'elixir_cost': card_info['elixir_cost'],
                        'rarity': card_info.get('rarity', 'Common')
                    }
                    json_db.append(card_entry_normal)
                    
                    # 2. Версия с эволюцией - в группе "With evolutions"
                    if evolution_path and evolution_path.exists():
                        try:
                            rel_evolution_path = str(evolution_path.relative_to(project_root))
                        except ValueError:
                            rel_evolution_path = str(evolution_path)
                        
                        card_entry_evolution = {
                            'name': f"{card_name}_evolution",  # Имя с подчеркиванием
                            'image_path': rel_evolution_path,
                            'has_evolution': True,
                            'group': 'With evolutions',  # Специальная группа для эволюций
                            'elixir_cost': card_info['elixir_cost'],
                            'rarity': card_info.get('rarity', 'Common')
                        }
                        json_db.append(card_entry_evolution)
                    else:
                        # Если эволюция не скачалась, все равно добавляем запись с путем к файлу эволюции
                        # (на случай, если эволюция будет доступна позже)
                        try:
                            rel_evolution_path = str(evolution_path.relative_to(project_root))
                        except ValueError:
                            rel_evolution_path = str(evolution_path)
                        
                        card_entry_evolution = {
                            'name': f"{card_name}_evolution",  # Имя с подчеркиванием
                            'image_path': rel_evolution_path,  # Путь к файлу эволюции (даже если файла нет)
                            'has_evolution': True,
                            'group': 'With evolutions',  # Специальная группа для эволюций
                            'elixir_cost': card_info['elixir_cost'],
                            'rarity': card_info.get('rarity', 'Common')
                        }
                        json_db.append(card_entry_evolution)
                else:
                    # Для карт без эволюции - одна запись
                    card_entry = {
                        'name': card_name,
                        'image_path': rel_image_path,
                        'has_evolution': False,
                        'group': card_info['group'],
                        'elixir_cost': card_info['elixir_cost'],
                        'rarity': card_info.get('rarity', 'Common')
                    }
                    json_db.append(card_entry)
                    
            except asyncio.CancelledError:
                logger.warning("Скачивание прервано пользователем")
                # Сохраняем частично скачанные данные
                if json_db:
                    json_path = cards_dir / "cards_database.json"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_db, f, ensure_ascii=False, indent=2)
                    logger.info(f"Частичные данные сохранены: {len(json_db)} карт")
                raise
            except Exception as e:
                logger.error(f"Ошибка при обработке карты {card_info.get('name', 'unknown')}: {e}")
                continue
    
    # Сохраняем JSON базу
    json_path = cards_dir / "cards_database.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_db, f, ensure_ascii=False, indent=2)
    
    logger.info(f"JSON база данных сохранена: {json_path}")
    logger.info(f"Всего карт в базе: {len(json_db)}")
    
    # Возвращаем относительный путь для JSON
    try:
        rel_json_path = str(json_path.relative_to(project_root))
    except ValueError:
        rel_json_path = str(json_path)
    
    return {'cards': json_db, 'json_path': rel_json_path}


def create_cards_from_web_data() -> List[Dict]:
    """Создает список карт из данных веб-поиска."""
    # Данные из веб-поиска и описания изображения
    all_cards = []
    
    # Список всех карт из веб-поиска (121 карта)
    cards_list = [
        # 1 эликсир
        "Skeletons", "Electro Spirit", "Fire Spirit", "Ice Spirit", "Heal Spirit",
        # 2 эликсир
        "Goblins", "Spear Goblins", "Bomber", "Bats", "Zap", "Giant Snowball", "Berserker",
        "Ice Golem", "Suspicious Bush", "Barbarian Barrel", "Wall Breakers", "Goblin Curse",
        "Rage", "The Log",
        # 3 эликсир
        "Archers", "Arrows", "Knight", "Minions", "Cannon", "Goblin Gang", "Skeleton Barrel",
        "Firecracker", "Royal Delivery", "Tombstone", "Mega Minion", "Dart Goblin", "Earthquake",
        "Elixir Golem", "Goblin Barrel", "Guards", "Skeleton Army", "Vines", "Clone", "Tornado",
        "Void", "Miner", "Princess", "Ice Wizard", "Royal Ghost", "Bandit", "Fisherman", "Little Prince",
        # 4 эликсир
        "Skeleton Dragons", "Mortar", "Tesla", "Fireball", "Mini P.E.K.K.A", "Musketeer",
        "Goblin Cage", "Goblin Hut", "Valkyrie", "Battle Ram", "Bomb Tower", "Flying Machine",
        "Hog Rider", "Battle Healer", "Furnace", "Zappies", "Goblin Demolisher", "Baby Dragon",
        "Dark Prince", "Freeze", "Poison", "Rune Giant", "Hunter", "Goblin Drill", "Witch",
        "Electro Wizard", "Inferno Dragon", "Phoenix", "Magic Archer", "Lumberjack", "Night Witch",
        "Mother Witch", "Golden Knight", "Skeleton King", "Mighty Miner",
        # 5 эликсир
        "Barbarians", "Minion Horde", "Rascals", "Giant", "Inferno Tower", "Wizard", "Royal Hogs",
        "Balloon", "Prince", "Electro Dragon", "Bowler", "Executioner", "Cannon Cart", "Ram Rider",
        "Graveyard", "Goblin Machine", "Archer Queen", "Goblinstein Monk",
        # 6 эликсир
        "Royal Giant", "Elite Barbarians", "Rocket", "Barbarian Hut", "Elixir Collector",
        "Giant Skeleton", "Lightning", "Goblin Giant", "X-Bow", "Sparky", "Spirit Empress", "Boss Bandit",
        # 7 эликсир
        "Royal Recruits", "P.E.K.K.A", "Electro Giant", "Mega Knight", "Lava Hound",
        # 8 эликсир
        "Golem",
        # 9 эликсир
        "Three Musketeers",
        # Дополнительные карты (Mirror и другие)
        "Mirror", "Empress"
    ]
    
    for card_name in cards_list:
        has_evolution = card_name in EVOLUTION_CARDS
        group = get_card_group(card_name)
        elixir = get_card_elixir_cost(card_name)
        rarity = get_card_rarity(card_name)
        
        all_cards.append({
            'name': card_name,
            'image_url': None,  # Будет заполнено при скачивании
            'card_url': None,
            'has_evolution': has_evolution,
            'group': group,
            'elixir_cost': elixir,
            'rarity': rarity
        })
    
    return all_cards
