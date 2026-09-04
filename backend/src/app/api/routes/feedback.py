"""Feedback API routes."""

from fastapi import APIRouter, status

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.feedback import service as feedback_service
from uuid import UUID

from app.features.schemas import FeedbackCreateRequest, FeedbackResponse, FeedbackUpdateRequest

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


@router.patch("/{feedback_id}")
async def update_feedback(
    feedback_id: UUID,
    request: FeedbackUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> FeedbackResponse:
    return await feedback_service.update_feedback(session, tenant.tenant_id, feedback_id, request)
