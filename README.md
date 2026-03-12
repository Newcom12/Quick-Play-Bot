# QuickPlayBot

QuickPlayBot - Telegram-бот для игры "Шпион" на `aiogram 3`, с PostgreSQL для хранения данных и Redis для FSM-состояний.

## Что умеет бот

- Регистрация пользователей по команде `/start`.
- Игра "Шпион" с настройкой количества игроков и шпионов.
- Поддержка карт Clash Royale, включая эволюции.
- Сохранение статистики игроков.
- Проверка подписки на канал и базовый rate limit.

## Технологический стек

- Python 3.13+
- aiogram 3.x
- SQLAlchemy + Alembic
- PostgreSQL (asyncpg)
- Redis (FSM storage)
- Docker + Docker Compose

## Структура проекта

```text
QuickPlayBot/
├── app/
│   ├── handlers/
│   │   ├── spy_game/
│   │   ├── help.py
│   │   ├── players.py
│   │   ├── rules.py
│   │   ├── start.py
│   │   └── stats.py
│   ├── middleware/
│   ├── utils/
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   └── models.py
├── alembic/
├── main.py
├── pyproject.toml
├── requirements.txt
├── setup.py
├── Dockerfile
└── docker-compose.yml
```

## Переменные окружения

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql+asyncpg://quickplay:quickplay@postgres:5432/quickplaybot
REDIS_URL=redis://redis:6379/0
CHANNEL_ID=@ваш_канал
GAME_TIMER_DURATION=150
LOG_LEVEL=INFO
LOG_FILE=app/data/logs/bot.log
LOG_ROTATION=10 MB
LOG_RETENTION=7 days
```

Примечания:

- `CHANNEL_ID` можно оставить пустым, если проверка подписки не нужна.
- Для приватного канала укажите числовой ID вида `-100...`.

## Локальная разработка без Docker

### 1. Установка зависимостей

Вариант через Poetry:

```bash
poetry install
```

Вариант через pip:

```bash
pip install -r requirements.txt
```

### 2. Применение миграций

```bash
alembic upgrade head
```

или

```bash
poetry run alembic upgrade head
```

### 3. Запуск бота

```bash
python main.py
```

или

```bash
poetry run python main.py
```

## Запуск через Docker Compose

### 1. Подготовка

- Убедитесь, что установлен Docker и Docker Compose.
- Заполните `.env` (минимум `BOT_TOKEN`).

### 2. Сборка и запуск

```bash
docker compose up --build -d
```

### 3. Просмотр логов

```bash
docker compose logs -f bot
```

### 4. Остановка

```bash
docker compose down
```

Для полной очистки с удалением томов:

```bash
docker compose down -v
```

## Миграции и база данных

- Миграции хранятся в `alembic/versions/`.
- URL базы берется из `DATABASE_URL`.
- В контейнерном запуске миграции применяются перед стартом бота.

Ручные команды:

```bash
alembic revision --autogenerate -m "описание_изменения"
alembic upgrade head
```

## FSM и Redis

- FSM-хранилище подключено через Redis в `app/bot.py`.
- URL берется из `REDIS_URL`.
- При остановке приложения FSM storage закрывается корректно.

## Подготовка к публикации и деплою

- Проверьте, что в репозитории нет секретов и реальных токенов.
- Добавьте рабочий пример в `.env.example` перед публичным релизом.
- Убедитесь, что миграции актуальны для текущих моделей.
- Проверьте запуск `docker compose up --build` на чистом окружении.
- Зафиксируйте зависимости через `requirements.txt` и `pyproject.toml`.

## Полезные команды

```bash
# Локальный запуск
python main.py

# Миграции
alembic upgrade head

# Docker
docker compose up --build -d
docker compose logs -f bot
docker compose down
```
