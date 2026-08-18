"""Campaign API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import require_roles
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import CampaignListResponse, CampaignResponse

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(require_roles("store_owner", "marketing_manager", "admin"))],
)


@router.get("")
def list_campaigns(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    channel: str | None = None,
) -> CampaignListResponse:
    return mock_services.list_campaigns(limit, offset)


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> CampaignResponse:
    return mock_services.campaign_response(campaign_id)
