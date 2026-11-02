"""Tenant repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant


async def get_tenant_by_id(session: AsyncSession, tenant_id: UUID) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def get_tenant_by_shop_id(session: AsyncSession, shop_id: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.shop_id == shop_id))
    return result.scalar_one_or_none()


async def get_tenant_by_shop_domain(session: AsyncSession, shop_domain: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.shop_domain == shop_domain))
    return result.scalar_one_or_none()


async def get_tenant_by_widget_public_key(session: AsyncSession, widget_public_key: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.widget_public_key == widget_public_key))
    return result.scalar_one_or_none()


async def get_enabled_public_widget_tenant(
    session: AsyncSession,
    *,
    shop_id: str | None,
    shop_domain: str | None,
    widget_public_key: str,
) -> Tenant | None:
    """Resolve one enabled widget from the complete supplied store identity."""
    criteria = [
        Tenant.widget_public_key == widget_public_key,
        Tenant.widget_enabled.is_(True),
    ]
    if shop_id is not None:
        criteria.append(Tenant.shop_id == shop_id)
    if shop_domain is not None:
        criteria.append(Tenant.shop_domain == shop_domain)

    result = await session.execute(select(Tenant).where(*criteria))
    return result.scalar_one_or_none()


async def update_tenant(session: AsyncSession, tenant: Tenant, updates: dict) -> Tenant:
    for field, value in updates.items():
        setattr(tenant, field, value)
    await session.commit()
    await session.refresh(tenant)
    return tenant
