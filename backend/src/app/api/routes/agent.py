"""Dashboard agent API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import EffectivePermissionsDep, require_permission, require_roles
from app.core.rbac import Permission, Role
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import agent as agent_service
from app.features.schemas import AgentToolListResponse, AgentToolResponse, AgentToolUpdateRequest

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(require_permission(Permission.USE_AGENT_TOOLS))],
)


@router.get("/tools")
async def list_agent_tools(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AgentToolListResponse:
    return await agent_service.list_agent_tools(
        session,
        tenant.tenant_id,
        limit=limit,
        offset=offset,
        effective_permissions=effective_permissions,
    )


@router.patch("/tools/{tool_name}", dependencies=[Depends(require_roles(Role.STORE_OWNER, Role.ADMIN))])
async def update_agent_tool(
    tool_name: str,
    request: AgentToolUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
) -> AgentToolResponse:
    return await agent_service.update_agent_tool(
        session, tenant.tenant_id, tool_name, request, effective_permissions
    )
