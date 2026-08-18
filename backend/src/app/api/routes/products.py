"""Product API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import ProductListResponse, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["active", "inactive", "archived"] | None = None,
    category: str | None = None,
) -> ProductListResponse:
    return mock_services.list_products(limit, offset)


@router.get("/{product_id}")
def get_product(
    product_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> ProductResponse:
    return mock_services.product_response(product_id)
