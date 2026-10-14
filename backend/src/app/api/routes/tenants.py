"""Tenant API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission, require_roles
from app.core.rbac import Permission, Role
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import tenants as tenant_service
from app.features.schemas import TenantResponse, TenantUpdateRequest

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
    dependencies=[Depends(require_roles(Role.STORE_OWNER, Role.ADMIN))],
)


@router.get("/{tenant_id}", dependencies=[Depends(require_permission(Permission.VIEW_TENANT))])
async def get_tenant(
    tenant_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> TenantResponse:
    return await tenant_service.get_tenant(session, tenant.tenant_id, tenant_id)


@router.patch("/{tenant_id}", dependencies=[Depends(require_permission(Permission.MANAGE_TENANT))])
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> TenantResponse:
    return await tenant_service.update_tenant(session, tenant.tenant_id, tenant_id, request)
