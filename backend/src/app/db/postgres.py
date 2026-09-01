"""Async PostgreSQL connection setup."""

from collections.abc import AsyncGenerator
from os import getenv

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def get_database_url() -> str:
    """Return the async SQLAlchemy database URL from the environment."""
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")
    return database_url


engine = create_async_engine(get_database_url(), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session