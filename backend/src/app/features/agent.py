"""Dashboard agent tool use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import agent_tools as agent_tool_repository
from app.core.permissions import forbidden
from app.core.rbac import Permission
from app.features.pagination import offset_pagination
from app.features.schemas import AgentToolListResponse, AgentToolResponse, AgentToolUpdateRequest


TOOL_DATA_PERMISSIONS: dict[str, Permission] = {
    "get_products": Permission.VIEW_PRODUCTS,
    "get_orders": Permission.VIEW_ORDERS,
    "get_sales": Permission.VIEW_SALES,
    "get_campaigns": Permission.VIEW_CAMPAIGNS,
}


async def list_agent_tools(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int,
    offset: int,
    effective_permissions: frozenset[Permission],
) -> AgentToolListResponse:
    allowed_names = frozenset(
        name for name, required in TOOL_DATA_PERMISSIONS.items()
        if required in effective_permissions
    )
    tools, total = await agent_tool_repository.list_agent_tools(
        session,
        tenant_id,
        limit=limit,
        offset=offset,
        allowed_names=allowed_names,
    )
    return offset_pagination(
        AgentToolListResponse,
        [
            AgentToolResponse(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
                read_only=tool.read_only,
            )
            for tool in tools if tool.name in allowed_names
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


async def update_agent_tool(
    session: AsyncSession,
    tenant_id: UUID,
    tool_name: str,
    request: AgentToolUpdateRequest,
    effective_permissions: frozenset[Permission] | None = None,
) -> AgentToolResponse:
    tool = await agent_tool_repository.get_tenant_agent_tool_by_name(session, tenant_id, tool_name)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Agent tool was not found."},
        )
    required = TOOL_DATA_PERMISSIONS.get(tool_name)
    if effective_permissions is None or required is None or required not in effective_permissions:
        raise forbidden()
    if not tool.read_only:
        raise forbidden()

    updates = {
        field: value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if updates.get("read_only") is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "Agent tools must remain read-only."},
        )

    if updates:
        tool = await agent_tool_repository.update_agent_tool(session, tool, updates)
    return AgentToolResponse(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
        read_only=tool.read_only,
    )
