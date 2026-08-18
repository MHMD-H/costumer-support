"""Order API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import OrderListResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def list_orders(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Literal["pending", "paid", "fulfilled", "cancelled", "refunded"] | None = None,
    user_id: UUID | None = None,
) -> OrderListResponse:
    return mock_services.list_orders(limit, offset)


@router.get("/{order_id}")
def get_order(
    order_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> OrderResponse:
    return mock_services.order_response(order_id)
