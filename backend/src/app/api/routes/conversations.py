"""Conversation API routes."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import EffectivePermissionsDep, require_conversation_access, require_permission
from app.core.rbac import Permission
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features.conversations import service as conversation_service
from app.features.schemas import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageListResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", dependencies=[Depends(require_conversation_access)])
async def list_conversations(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
    status_filter: Annotated[Literal["active", "archived"] | None, Query(alias="status")] = None,
) -> ConversationListResponse:
    return await conversation_service.list_conversations(
        session,
        tenant.tenant_id,
        status=status_filter,
        limit=limit,
        cursor=cursor,
        viewer_id=current_user.id,
        own_only=Permission.VIEW_CONVERSATIONS not in effective_permissions,
    )


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission(Permission.CREATE_CONVERSATIONS))])
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


@router.get("/{conversation_id}", dependencies=[Depends(require_conversation_access)])
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
) -> ConversationResponse:
    return await conversation_service.get_conversation(
        session,
        tenant.tenant_id,
        conversation_id,
        viewer_id=current_user.id,
        own_only=Permission.VIEW_CONVERSATIONS not in effective_permissions,
    )


@router.patch("/{conversation_id}", dependencies=[Depends(require_conversation_access)])
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdateRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
) -> ConversationResponse:
    return await conversation_service.update_conversation(
        session,
        tenant.tenant_id,
        conversation_id,
        request,
        viewer_id=current_user.id,
        own_only=Permission.VIEW_CONVERSATIONS not in effective_permissions,
    )


@router.get("/{conversation_id}/messages", dependencies=[Depends(require_conversation_access)])
async def list_messages(
    conversation_id: UUID,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> MessageListResponse:
    return await conversation_service.list_messages(
        session,
        tenant.tenant_id,
        conversation_id,
        limit=limit,
        cursor=cursor,
        viewer_id=current_user.id,
        own_only=Permission.VIEW_CONVERSATIONS not in effective_permissions,
        allow_document_sources=Permission.VIEW_DOCUMENTS in effective_permissions,
    )
