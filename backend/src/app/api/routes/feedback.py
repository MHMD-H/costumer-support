"""Feedback API routes."""

from fastapi import APIRouter, status

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.feedback import service as feedback_service
from app.features.schemas import FeedbackCreateRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: FeedbackCreateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> FeedbackResponse:
    return await feedback_service.create_feedback(
        session,
        tenant.tenant_id,
        current_user.id,
        request,
    )
