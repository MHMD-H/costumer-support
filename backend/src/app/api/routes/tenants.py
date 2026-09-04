"""Tenant API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import tenants as tenant_service
from app.features.schemas import TenantResponse, TenantUpdateRequest

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
    dependencies=[Depends(require_roles("store_owner", "admin"))],
)


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> TenantResponse:
    return await tenant_service.get_tenant(session, tenant.tenant_id, tenant_id)


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> TenantResponse:
    return await tenant_service.update_tenant(session, tenant.tenant_id, tenant_id, request)
