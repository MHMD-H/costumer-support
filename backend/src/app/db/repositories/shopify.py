"""Persistence helpers for Shopify OAuth state and connections."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ShopifyConnection, ShopifyOAuthState, Tenant, User


async def create_oauth_state(
    session: AsyncSession, *, user_id: UUID, state_hash: str, expires_at: datetime
) -> ShopifyOAuthState:
    oauth_state = ShopifyOAuthState(
        user_id=user_id, state_hash=state_hash, expires_at=expires_at
    )
    session.add(oauth_state)
    await session.commit()
    await session.refresh(oauth_state)
    return oauth_state


async def consume_oauth_state(
    session: AsyncSession, *, state_hash: str, consumed_at: datetime
) -> ShopifyOAuthState | None:
    result = await session.execute(
        update(ShopifyOAuthState)
        .where(
            ShopifyOAuthState.state_hash == state_hash,
            ShopifyOAuthState.consumed_at.is_(None),
            ShopifyOAuthState.expires_at > consumed_at,
        )
        .values(consumed_at=consumed_at)
        .returning(ShopifyOAuthState)
    )
    oauth_state = result.scalar_one_or_none()
    await session.commit()
    return oauth_state


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_connection_by_shop_id(
    session: AsyncSession, shop_id: str
) -> ShopifyConnection | None:
    result = await session.execute(
        select(ShopifyConnection).where(ShopifyConnection.shop_id == shop_id)
    )
    return result.scalar_one_or_none()


async def get_connection_by_tenant_id(
    session: AsyncSession, tenant_id: UUID
) -> ShopifyConnection | None:
    result = await session.execute(
        select(ShopifyConnection).where(ShopifyConnection.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_tenant(
    session: AsyncSession, *, name: str, shop_id: str, shop_domain: str
) -> Tenant:
    tenant = Tenant(name=name, shop_id=shop_id, shop_domain=shop_domain)
    session.add(tenant)
    await session.flush()
    return tenant


async def create_connection(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    shop_id: str,
    shop_domain: str,
    access_token_encrypted: str,
) -> ShopifyConnection:
    connection = ShopifyConnection(
        tenant_id=tenant_id,
        shop_id=shop_id,
        shop_domain=shop_domain,
        access_token_encrypted=access_token_encrypted,
    )
    session.add(connection)
    await session.flush()
    return connection
