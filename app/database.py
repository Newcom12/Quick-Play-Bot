"""Настройка базы данных через SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Создание движка базы данных
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """Генератор сессии базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация базы данных - создание всех таблиц."""
    Base.metadata.create_all(bind=engine)
