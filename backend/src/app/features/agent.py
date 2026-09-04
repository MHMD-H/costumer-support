"""Dashboard agent tool use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import agent_tools as agent_tool_repository
from app.features.schemas import AgentToolListResponse, AgentToolResponse, AgentToolUpdateRequest


async def list_agent_tools(session: AsyncSession, tenant_id: UUID) -> AgentToolListResponse:
    tools = await agent_tool_repository.list_agent_tools(session, tenant_id)
    return AgentToolListResponse(
        items=[
            AgentToolResponse(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
                read_only=tool.read_only,
            )
            for tool in tools
        ]
    )


async def update_agent_tool(
    session: AsyncSession,
    tenant_id: UUID,
    tool_name: str,
    request: AgentToolUpdateRequest,
) -> AgentToolResponse:
    tool = await agent_tool_repository.get_tenant_agent_tool_by_name(session, tenant_id, tool_name)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Agent tool was not found."},
        )

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
