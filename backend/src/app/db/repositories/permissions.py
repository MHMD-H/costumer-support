"""Permission repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Permission
from app.db.repositories.common import count_for_statement


async def get_permission_by_id(session: AsyncSession, tenant_id: UUID, permission_id: UUID) -> Permission | None:
    result = await session.execute(
        select(Permission).where(Permission.tenant_id == tenant_id, Permission.id == permission_id)
    )
    return result.scalar_one_or_none()


async def get_permission_by_value(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    permission: str,
) -> Permission | None:
    result = await session.execute(
        select(Permission).where(
            Permission.tenant_id == tenant_id,
            Permission.user_id == user_id,
            Permission.permission == permission,
        )
    )
    return result.scalar_one_or_none()


async def list_permissions(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    user_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Permission], int]:
    criteria = [Permission.tenant_id == tenant_id]
    if user_id is not None:
        criteria.append(Permission.user_id == user_id)

    statement = select(Permission).where(*criteria).order_by(Permission.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def update_permission(session: AsyncSession, permission: Permission, updates: dict) -> Permission:
    for field, value in updates.items():
        setattr(permission, field, value)
    await session.commit()
    await session.refresh(permission)
    return permission
