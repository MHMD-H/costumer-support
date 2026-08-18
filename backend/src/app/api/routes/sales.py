"""Sales API routes."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import SalesSummaryRequest, SalesSummaryResponse

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post(
    "/summary",
    dependencies=[Depends(require_roles("store_owner", "team_member", "admin"))],
)
def get_sales_summary(
    request: SalesSummaryRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> SalesSummaryResponse:
    return mock_services.sales_summary(request)
