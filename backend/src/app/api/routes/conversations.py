"""Conversation API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.conversations import service as conversation_service
from app.features.schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[Literal["active", "archived"] | None, Query(alias="status")] = None,
) -> ConversationListResponse:
    return await conversation_service.list_conversations(
        session,
        tenant.tenant_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> ConversationResponse:
    return await conversation_service.create_conversation(
        session,
        tenant.tenant_id,
        current_user.id,
        request,
    )


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> ConversationResponse:
    return await conversation_service.get_conversation(
        session,
        tenant.tenant_id,
        conversation_id,
    )


@router.get("/{conversation_id}/messages")
async def list_messages(
    conversation_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageListResponse:
    return await conversation_service.list_messages(
        session,
        tenant.tenant_id,
        conversation_id,
        limit=limit,
        offset=offset,
    )
