"""User repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.common import count_for_statement


async def get_user_by_id(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.tenant_id == tenant_id, User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_auth_user_id(session: AsyncSession, auth_user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.auth_user_id == auth_user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, tenant_id: UUID, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    statement = select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def create_user(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    auth_user_id: UUID,
    name: str,
    email: str,
    role: str,
) -> User:
    user = User(
        tenant_id=tenant_id,
        auth_user_id=auth_user_id,
        name=name,
        email=email,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, updates: dict) -> User:
    for field, value in updates.items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user
