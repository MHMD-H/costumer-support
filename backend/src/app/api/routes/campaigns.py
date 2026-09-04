"""Campaign API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.commerce import campaigns as campaign_service
from app.features.schemas import (
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdateRequest,
)

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_roles("store_owner", "marketing_manager", "admin"))],
)


@router.get("")
async def list_campaigns(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    channel: str | None = None,
) -> CampaignListResponse:
    return await campaign_service.list_campaigns(
        session,
        tenant.tenant_id,
        channel=channel,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CampaignCreateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> CampaignResponse:
    return await campaign_service.create_campaign(session, tenant.tenant_id, request)


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> CampaignResponse:
    return await campaign_service.get_campaign(session, tenant.tenant_id, campaign_id)


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: UUID,
    request: CampaignUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> CampaignResponse:
    return await campaign_service.update_campaign(session, tenant.tenant_id, campaign_id, request)
