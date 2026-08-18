"""Dashboard agent API routes."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import AgentToolListResponse

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(require_permission("use_agent_tools"))],
)


@router.get("/tools")
def list_agent_tools(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> AgentToolListResponse:
    return mock_services.list_agent_tools()
