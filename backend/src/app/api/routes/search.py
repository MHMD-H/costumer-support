"""Search API routes."""

from fastapi import APIRouter

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
def search(
    request: SearchRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> SearchResponse:
    return mock_services.search(request)
