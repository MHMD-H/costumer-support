"""Campaign analytics use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign
from app.db.repositories import campaigns as campaign_repository
from app.features.pagination import page
from app.features.schemas import CampaignListResponse, CampaignResponse


def to_campaign_response(campaign: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        name=campaign.name,
        channel=campaign.channel,
        spend=campaign.spend,
        revenue=campaign.revenue,
        roas=campaign.roas,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


async def list_campaigns(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    channel: str | None,
    limit: int,
    offset: int,
) -> CampaignListResponse:
    campaigns, total = await campaign_repository.list_campaigns(
        session,
        tenant_id,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return CampaignListResponse(
        items=[to_campaign_response(campaign) for campaign in campaigns],
        page=page(limit, offset, total),
    )


async def get_campaign(session: AsyncSession, tenant_id: UUID, campaign_id: UUID) -> CampaignResponse:
    campaign = await campaign_repository.get_campaign_by_id(session, tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Campaign was not found."},
        )
    return to_campaign_response(campaign)
