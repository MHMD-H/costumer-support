"""Dashboard agent API routes."""

from fastapi import APIRouter, Depends

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_permission
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import agent as agent_service
from app.features.schemas import AgentToolListResponse, AgentToolResponse, AgentToolUpdateRequest

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(require_permission("use_agent_tools"))],
)


@router.get("/tools")
async def list_agent_tools(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> AgentToolListResponse:
    return await agent_service.list_agent_tools(session, tenant.tenant_id)


@router.patch("/tools/{tool_name}")
async def update_agent_tool(
    tool_name: str,
    request: AgentToolUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> AgentToolResponse:
    return await agent_service.update_agent_tool(session, tenant.tenant_id, tool_name, request)
