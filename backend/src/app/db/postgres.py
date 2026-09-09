"""Async PostgreSQL connection setup."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from os import getenv
from typing import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def get_database_url() -> str:
    """Return the async SQLAlchemy database URL from the environment."""
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")
    return database_url


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return create_async_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session


async def validate_database_connection() -> None:
    """Validate database connectivity when DATABASE_URL is configured."""
    if not getenv("DATABASE_URL"):
        return

    async with get_engine().connect() as connection:
        await connection.execute(text("select 1"))


async def dispose_engine() -> None:
    """Dispose the cached async engine during application shutdown."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()

    get_sessionmaker.cache_clear()
    get_engine.cache_clear()


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
