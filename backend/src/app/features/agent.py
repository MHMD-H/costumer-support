"""Dashboard agent tool use cases."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import agent_tools as agent_tool_repository
from app.features.schemas import AgentToolListResponse, AgentToolResponse


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
