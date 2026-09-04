"""Agent tool repository."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentTool


async def list_agent_tools(session: AsyncSession, tenant_id: UUID) -> list[AgentTool]:
    result = await session.execute(
        select(AgentTool)
        .where(
            or_(AgentTool.tenant_id == tenant_id, AgentTool.tenant_id.is_(None)),
            AgentTool.read_only.is_(True),
        )
        .order_by(AgentTool.name.asc())
    )
    return list(result.scalars().all())


async def get_tenant_agent_tool_by_name(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
) -> AgentTool | None:
    result = await session.execute(
        select(AgentTool).where(
            AgentTool.tenant_id == tenant_id,
            AgentTool.name == name,
        )
    )
    return result.scalar_one_or_none()


async def update_agent_tool(session: AsyncSession, tool: AgentTool, updates: dict) -> AgentTool:
    for field, value in updates.items():
        setattr(tool, field, value)
    await session.commit()
    await session.refresh(tool)
    return tool
