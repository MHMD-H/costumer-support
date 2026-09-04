"""Permission API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import permissions as permission_service
from app.features.schemas import PermissionListResponse, PermissionResponse, PermissionUpdateRequest

router = APIRouter(
    prefix="/permissions",
    tags=["permissions"],
    dependencies=[Depends(require_roles("store_owner", "admin"))],
)


@router.get("")
async def list_permissions(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    user_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PermissionListResponse:
    return await permission_service.list_permissions(
        session,
        tenant.tenant_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )


@router.patch("/{permission_id}")
async def update_permission(
    permission_id: UUID,
    request: PermissionUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> PermissionResponse:
    return await permission_service.update_permission(session, tenant.tenant_id, permission_id, request)
