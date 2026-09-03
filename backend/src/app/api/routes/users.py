"""User API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.schemas import UserListResponse, UserResponse
from app.features.users import service as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", dependencies=[Depends(require_roles("store_owner", "admin"))])
async def list_users(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    return await user_service.list_users(session, tenant.tenant_id, limit=limit, offset=offset)


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> UserResponse:
    return await user_service.get_user(session, tenant.tenant_id, user_id)
