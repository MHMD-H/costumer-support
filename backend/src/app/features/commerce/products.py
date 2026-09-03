"""Product use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product
from app.db.repositories import products as product_repository
from app.features.pagination import page
from app.features.schemas import ProductListResponse, ProductResponse


def to_product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        external_product_id=product.external_product_id,
        name=product.name,
        description=product.description,
        category=product.category,
        price=product.price,
        status=product.status,
        public_visible=product.public_visible,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def list_products(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    status: str | None,
    category: str | None,
    limit: int,
    offset: int,
) -> ProductListResponse:
    products, total = await product_repository.list_products(
        session,
        tenant_id,
        status=status,
        category=category,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[to_product_response(product) for product in products],
        page=page(limit, offset, total),
    )


async def get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> ProductResponse:
    product = await product_repository.get_product_by_id(session, tenant_id, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Product was not found."},
        )
    return to_product_response(product)
