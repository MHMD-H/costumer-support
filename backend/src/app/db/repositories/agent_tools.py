"""Agent tool repository."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AgentTool
from app.db.repositories.common import count_for_statement


async def list_agent_tools(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[AgentTool], int]:
    statement = (
        select(AgentTool)
        .options(selectinload(AgentTool.tenant))
        .where(
            or_(AgentTool.tenant_id == tenant_id, AgentTool.tenant_id.is_(None)),
            AgentTool.read_only.is_(True),
        )
        .order_by(AgentTool.created_at.desc(), AgentTool.id.desc())
    )
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def get_tenant_agent_tool_by_name(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
) -> AgentTool | None:
    result = await session.execute(
        select(AgentTool).options(selectinload(AgentTool.tenant)).where(
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
