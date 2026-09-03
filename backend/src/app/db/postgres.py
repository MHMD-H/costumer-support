"""Async PostgreSQL connection setup."""

from collections.abc import AsyncGenerator
from functools import lru_cache
from os import getenv
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def get_database_url() -> str:
    """Return the async SQLAlchemy database URL from the environment."""
    database_url = getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")
    return database_url


@lru_cache(maxsize=1)
def get_engine():
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


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
