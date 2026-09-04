"""Campaign repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign
from app.db.repositories.common import count_for_statement


async def get_campaign_by_id(session: AsyncSession, tenant_id: UUID, campaign_id: UUID) -> Campaign | None:
    result = await session.execute(
        select(Campaign).where(Campaign.tenant_id == tenant_id, Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()


async def list_campaigns(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    channel: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Campaign], int]:
    criteria = [Campaign.tenant_id == tenant_id]
    if channel is not None:
        criteria.append(Campaign.channel == channel)

    statement = select(Campaign).where(*criteria).order_by(Campaign.created_at.desc())
    total = await count_for_statement(session, statement)
    result = await session.execute(statement.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def get_campaign_by_name_and_channel(
    session: AsyncSession,
    tenant_id: UUID,
    name: str,
    channel: str,
) -> Campaign | None:
    result = await session.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.name == name,
            Campaign.channel == channel,
        )
    )
    return result.scalar_one_or_none()


async def create_campaign(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    name: str,
    channel: str,
    spend,
    revenue,
    roas,
) -> Campaign:
    campaign = Campaign(
        tenant_id=tenant_id,
        name=name,
        channel=channel,
        spend=spend,
        revenue=revenue,
        roas=roas,
    )
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def update_campaign(session: AsyncSession, campaign: Campaign, updates: dict) -> Campaign:
    for field, value in updates.items():
        setattr(campaign, field, value)
    await session.commit()
    await session.refresh(campaign)
    return campaign
