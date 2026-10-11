"""Sales API routes."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission, require_roles
from app.core.rbac import Permission, Role
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.commerce import sales as sales_service
from app.features.schemas import SalesSummaryRequest, SalesSummaryResponse

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post(
    "/summary",
    dependencies=[
        Depends(require_roles(Role.STORE_OWNER, Role.TEAM_MEMBER, Role.ADMIN)),
        Depends(require_permission(Permission.VIEW_SALES)),
    ],
)
async def get_sales_summary(
    request: SalesSummaryRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> SalesSummaryResponse:
    return await sales_service.get_sales_summary(session, tenant.tenant_id, request)
