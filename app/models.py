"""Модели базы данных."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class ClashRoyaleCard(Base):
    """Модель карты Clash Royale."""

    __tablename__ = "clash_royale_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    file_id = Column(String, nullable=True)  # Telegram file_id для изображения
    file_id_evolution = Column(String, nullable=True)  # Telegram file_id для изображения эволюции
    has_evolution = Column(Boolean, default=False, nullable=False)
    group = Column(String, nullable=False)  # Spells, Melee, Ranged и т.д.
    elixir_cost = Column(Integer, nullable=False)
    rarity = Column(String, nullable=True)  # Common, Rare, Epic, Legendary, Champion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ClashRoyaleCard(name={self.name}, elixir={self.elixir_cost}, has_evolution={self.has_evolution})>"


class SpyCard(Base):
    """Модель карты для игры в шпиона (универсальная для разных игр)."""

    __tablename__ = "spy_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    file_id = Column(String, nullable=True)  # Telegram file_id для изображения
    game_name = Column(String, nullable=True)  # Название игры (например, "Clash Royale", "Brawl Stars" и т.д.)
    description = Column(String, nullable=True)  # Описание карты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SpyCard(name={self.name}, game={self.game_name})>"


class PlayerStats(Base):
    """Модель статистики игрока в игре Шпион."""

    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True, nullable=False)  # Имя игрока
    games_played = Column(Integer, default=0, nullable=False)  # Всего игр
    wins = Column(Integer, default=0, nullable=False)  # Всего побед
    wins_by_guessing = Column(Integer, default=0, nullable=False)  # Побед угадыванием темы (как шпион)
    wins_by_last_standing = Column(Integer, default=0, nullable=False)  # Побед как последний оставшийся
    wins_by_timer = Column(Integer, default=0, nullable=False)  # Побед по таймеру
    losses = Column(Integer, default=0, nullable=False)  # Поражений
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PlayerStats(player_name={self.player_name}, wins={self.wins}, games={self.games_played})>"


class SavedPlayer(Base):
    """Модель сохраненного игрока (для быстрого доступа)."""

    __tablename__ = "saved_players"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)  # ID пользователя Telegram (владелец списка)
    name = Column(String, nullable=False)  # Имя игрока
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SavedPlayer(user_id={self.user_id}, name={self.name})>"
