"""
Подключение к базе данных SQLAlchemy
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Создание асинхронного движка
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Логирование SQL-запросов в режиме отладки
    future=True,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)

# Базовый класс для моделей
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии БД.
    Используется в роутерах FastAPI.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Инициализация БД (создание таблиц)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
