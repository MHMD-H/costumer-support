"""User API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import UserListResponse, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", dependencies=[Depends(require_roles("store_owner", "admin"))])
def list_users(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    return mock_services.list_users(limit, offset)


@router.get("/{user_id}")
def get_user(
    user_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> UserResponse:
    return mock_services.user_response(user_id)
