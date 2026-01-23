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
