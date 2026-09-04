"""Campaign analytics use cases."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign
from app.db.repositories import campaigns as campaign_repository
from app.features.pagination import page
from app.features.schemas import CampaignCreateRequest, CampaignListResponse, CampaignResponse, CampaignUpdateRequest


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


async def create_campaign(
    session: AsyncSession,
    tenant_id: UUID,
    request: CampaignCreateRequest,
) -> CampaignResponse:
    existing = await campaign_repository.get_campaign_by_name_and_channel(
        session,
        tenant_id,
        request.name,
        request.channel,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "A campaign with this name and channel already exists."},
        )

    campaign = await campaign_repository.create_campaign(
        session,
        tenant_id=tenant_id,
        name=request.name,
        channel=request.channel,
        spend=request.spend,
        revenue=request.revenue,
        roas=request.roas,
    )
    return to_campaign_response(campaign)


async def update_campaign(
    session: AsyncSession,
    tenant_id: UUID,
    campaign_id: UUID,
    request: CampaignUpdateRequest,
) -> CampaignResponse:
    campaign = await campaign_repository.get_campaign_by_id(session, tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Campaign was not found."},
        )

    updates = {
        field: value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    name = updates.get("name", campaign.name)
    channel = updates.get("channel", campaign.channel)
    if (name, channel) != (campaign.name, campaign.channel):
        existing = await campaign_repository.get_campaign_by_name_and_channel(session, tenant_id, name, channel)
        if existing is not None and existing.id != campaign.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "conflict", "message": "A campaign with this name and channel already exists."},
            )

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        campaign = await campaign_repository.update_campaign(session, campaign, updates)
    return to_campaign_response(campaign)
