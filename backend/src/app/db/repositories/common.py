"""Shared repository helpers."""

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def count_for_statement(session: AsyncSession, statement: Select[Any]) -> int:
    count_statement = select(func.count()).select_from(statement.order_by(None).limit(None).offset(None).subquery())
    result = await session.execute(count_statement)
    return int(result.scalar_one())
