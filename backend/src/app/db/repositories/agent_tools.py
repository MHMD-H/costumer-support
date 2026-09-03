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
