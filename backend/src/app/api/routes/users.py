"""User API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission, require_roles
from app.core.rbac import Permission, Role
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.schemas import UserListResponse, UserResponse, UserUpdateRequest
from app.features.users import service as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", dependencies=[
    Depends(require_roles(Role.STORE_OWNER, Role.ADMIN)),
    Depends(require_permission(Permission.VIEW_USERS)),
])
async def list_users(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    return await user_service.list_users(session, tenant.tenant_id, limit=limit, offset=offset)


@router.get("/{user_id}", dependencies=[Depends(require_permission(Permission.VIEW_USERS))])
async def get_user(
    user_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> UserResponse:
    return await user_service.get_user(session, tenant.tenant_id, user_id)


@router.patch("/{user_id}", dependencies=[
    Depends(require_roles(Role.STORE_OWNER, Role.ADMIN)),
    Depends(require_permission(Permission.MANAGE_USERS)),
])
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> UserResponse:
    return await user_service.update_user(
        session, tenant.tenant_id, user_id, request, acting_user=current_user
    )
