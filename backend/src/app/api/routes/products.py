"""Product API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.commerce import products as product_service
from app.features.schemas import ProductListResponse, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["active", "inactive", "archived"] | None = None,
    category: str | None = None,
) -> ProductListResponse:
    return await product_service.list_products(
        session,
        tenant.tenant_id,
        status=status,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}")
async def get_product(
    product_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> ProductResponse:
    return await product_service.get_product(session, tenant.tenant_id, product_id)
