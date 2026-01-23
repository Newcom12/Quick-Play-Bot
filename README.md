# QuickPlayBot

Telegram бот с базой данных SQLite3, построенный на aiogram 3.x.

## 📋 Описание

QuickPlayBot - это структурированный телеграм бот с поддержкой базы данных, логирования и современной архитектурой.

## 🏗️ Архитектура проекта

```
QuickPlayBot/
├── main.py                 # Точка входа в приложение
├── app/                    # Основное приложение
│   ├── __init__.py
│   ├── config.py          # Конфигурация через pydantic_settings
│   ├── database.py        # Настройка SQLAlchemy и SQLite3
│   ├── models.py          # Модели базы данных
│   ├── bot.py             # Инициализация бота и диспетчера
│   ├── handlers/          # Обработчики команд и сообщений
│   │   ├── __init__.py
│   │   └── start.py       # Обработчик команды /start
│   └── utils/             # Утилиты
│       ├── __init__.py
│       ├── logger.py      # Настройка loguru
│       ├── card_parser.py # Парсер карт Clash Royale
│       └── download_cards.py # Скрипт скачивания карт
├── .env                   # Переменные окружения
├── .gitignore
├── pyproject.toml         # Зависимости проекта
└── README.md              # Документация
```

## 🔧 Технологии

- **aiogram 3.x** - Асинхронный фреймворк для Telegram Bot API
- **SQLAlchemy** - ORM для работы с базой данных
- **SQLite3** - Легковесная база данных
- **pydantic-settings** - Управление конфигурацией через .env
- **loguru** - Продвинутое логирование с ротацией файлов

## 🚀 Установка и запуск

### 1. Установка зависимостей

```bash
poetry install
```

или

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта и укажите токен бота:

```env
BOT_TOKEN=your_bot_token_here
```

### 3. Запуск бота

```bash
python main.py
```

## 📚 Логика приложения

### Инициализация

1. **Загрузка конфигурации** (`app/config.py`)
   - Чтение переменных окружения через `pydantic_settings`
   - Настройки бота, базы данных и логирования

2. **Инициализация базы данных** (`app/database.py`)
   - Создание движка SQLAlchemy для SQLite3
   - Создание фабрики сессий
   - Автоматическое создание таблиц при первом запуске

3. **Настройка логирования** (`app/utils/logger.py`)
   - Консольный вывод с цветами
   - Файловое логирование с ротацией
   - Настраиваемые уровни логирования

4. **Инициализация бота** (`app/bot.py`)
   - Создание экземпляра бота с HTML parse mode
   - Настройка диспетчера
   - Регистрация команд через `set_my_commands`

### Обработка команд

#### `/start` - Начало работы

**Обработчик:** `app/handlers/start.py`

**Логика:**
1. Получение информации о пользователе из сообщения
2. Проверка существования пользователя в базе данных
3. Если пользователь новый:
   - Создание записи в таблице `users`
   - Сохранение telegram_id, username, first_name, last_name
4. Если пользователь существует:
   - Обновление информации о пользователе
5. Отправка приветственного сообщения с HTML форматированием
6. Логирование всех действий

**Модель User:**
- `id` - Первичный ключ
- `telegram_id` - Уникальный ID пользователя в Telegram
- `username` - Имя пользователя (@username)
- `first_name` - Имя
- `last_name` - Фамилия
- `is_active` - Статус активности
- `created_at` - Дата создания записи
- `updated_at` - Дата последнего обновления

### Работа с базой данных

- Использование SQLAlchemy ORM для всех операций
- Автоматическое управление сессиями через контекстные менеджеры
- Миграции через `Base.metadata.create_all()`

### Логирование

- Все события логируются через `loguru`
- Логи сохраняются в `logs/bot.log`
- Автоматическая ротация при достижении 10 MB
- Хранение логов за последние 7 дней
- Сжатие старых логов в zip

## 📝 Добавление новых функций

### Добавление новой команды

1. Создайте файл обработчика в `app/handlers/`
2. Создайте роутер и обработчик:

```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("your_command"))
async def cmd_your_command(message: Message):
    await message.answer("Ответ на команду")
```

3. Зарегистрируйте роутер в `main.py`:

```python
from app.handlers import your_handler
dp.include_router(your_handler.router)
```

4. Добавьте команду в `app/bot.py` в функцию `set_bot_commands()`

### Добавление новой модели

1. Создайте модель в `app/models.py`:

```python
class YourModel(Base):
    __tablename__ = "your_table"
    id = Column(Integer, primary_key=True)
    # ... другие поля
```

2. Таблица будет создана автоматически при следующем запуске

## 🔒 Безопасность

- `.env` файл добавлен в `.gitignore`
- Токен бота хранится только в переменных окружения
- База данных хранится локально

## 🃏 Работа с картами Clash Royale

### Скачивание карт

Для скачивания всех карт Clash Royale с сайта deckshop.pro используйте скрипт:

```bash
poetry run python -m app.utils.download_cards
```

или

```bash
cd app/utils && poetry run python download_cards.py
```

**Что делает скрипт:**
1. Парсит сайт https://www.deckshop.pro/card/list для получения URL изображений
2. Скачивает изображения всех 121 карт в папку `app/data/cards/`
3. Для карт с эволюцией (39 штук) скачивает два варианта:
   - Обычная карта: `{card_name}.png`
   - Карта с эволюцией: `{card_name}_evolution.png`
4. Создает JSON базу данных `app/data/cards/cards_database.json` с **160 записями** (121 обычных + 39 эволюций)

**Доскачивание недостающих карт:**

Если некоторые карты не скачались, используйте отдельный скрипт:

```bash
poetry run python -m app.utils.download_missing_cards
```

Этот скрипт пытается скачать только те карты, которые не удалось скачать при основном запуске.

**Структура JSON базы данных:**

Для карт **БЕЗ эволюции** (82 карты):
```json
{
  "name": "Goblins",
  "image_path": "app/data/cards/Goblins.png",
  "has_evolution": false,
  "group": "Melee",
  "elixir_cost": 2,
  "rarity": "Common"
}
```

Для карт **С эволюцией** создаются **ДВЕ отдельные записи**:

1. **Обычная версия** (в обычной группе):
```json
{
  "name": "Skeletons",
  "image_path": "app/data/cards/Skeletons.png",
  "has_evolution": false,
  "group": "Melee",
  "elixir_cost": 1,
  "rarity": "Common"
}
```

2. **Версия с эволюцией** (в группе "With evolutions"):
```json
{
  "name": "Skeletons_evolution",
  "image_path": "app/data/cards/Skeletons_evolution.png",
  "has_evolution": true,
  "group": "With evolutions",
  "elixir_cost": 1,
  "rarity": "Common"
}
```

### Структура данных карт

Каждая карта содержит:
- `name` - Название карты (для эволюций: `{card_name}_evolution`)
- `image_path` - Путь к изображению карты
- `has_evolution` - Флаг наличия эволюции (True для эволюций, False для обычных версий)
- `group` - Группа карты
- `elixir_cost` - Стоимость в эликсире (1-9)
- `rarity` - Редкость (Common, Rare, Epic, Legendary, Champion)

### Особенности работы с картами

- **Всего карт:** 121 обычная карта + 39 эволюций = **160 записей в JSON**

- **39 карт с эволюцией** сохраняются как **ДВЕ отдельные записи**:
  - **Обычная версия** (has_evolution=False):
    - Имя: `{card_name}` (например, "Skeletons")
    - Файл: `{card_name}.png`
    - Группа: обычная группа (Melee, Ranged, Spells и т.д.)
  - **Версия с эволюцией** (has_evolution=True):
    - Имя: `{card_name}_evolution` (например, "Skeletons_evolution")
    - Файл: `{card_name}_evolution.png`
    - Группа: **"With evolutions"** (специальная группа)
  
- **Группы карт:**
  - **With evolutions** - все 39 карт с эволюцией (только версии с эволюцией)
  - Spells (Заклинания)
  - Melee (Ближний бой)
  - Ranged (Дальний бой)
  - Buildings (Здания)
  - Air units (Воздушные юниты)
  - Ground units (Наземные юниты)

- **Редкость карт:**
  - Common (Обычная)
  - Rare (Редкая)
  - Epic (Эпическая)
  - Legendary (Легендарная)
  - Champion (Чемпион)

- **Формат изображений:** Все изображения сохраняются в формате PNG для максимального качества

- **Примечания:**
  - Если парсинг сайта не удался, скрипт использует предопределенный список карт
  - Изображения скачиваются в полном размере, если доступны
  - Все ошибки логируются в `app/data/logs/bot.log`

### Модель Card в базе данных

**Модель Card:**
- `id` - Первичный ключ
- `name` - Название карты (уникальное)
- `image_path` - Путь к изображению обычной карты
- `image_path_evolution` - Путь к изображению с эволюцией
- `has_evolution` - Флаг наличия эволюции
- `group` - Группа карты
- `elixir_cost` - Стоимость в эликсире
- `rarity` - Редкость карты
- `created_at` - Дата создания записи
- `updated_at` - Дата последнего обновления

## 📄 Лицензия

Проект создан для личного использования.
