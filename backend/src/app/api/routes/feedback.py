"""Feedback API routes."""

from fastapi import APIRouter, status

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import FeedbackCreateRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(
    request: FeedbackCreateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> FeedbackResponse:
    return mock_services.create_feedback(request)
