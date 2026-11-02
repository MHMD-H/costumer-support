"""Product repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Product
from app.db.repositories.common import count_for_statement


async def get_product_by_id(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product | None:
    result = await session.execute(
        select(Product)
        .options(selectinload(Product.tenant))
        .where(Product.tenant_id == tenant_id, Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def get_public_product_by_external_id(
    session: AsyncSession, tenant_id: UUID, external_product_id: str
) -> Product | None:
    """Return only a public-visible product owned by the resolved tenant."""
    result = await session.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.external_product_id == external_product_id,
            Product.public_visible.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_products(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    category: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Product], int]:
    criteria = [Product.tenant_id == tenant_id]
    if status is not None:
        criteria.append(Product.status == status)
    if category is not None:
        criteria.append(Product.category == category)

    statement = select(Product).where(*criteria).order_by(Product.created_at.desc(), Product.id.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total
