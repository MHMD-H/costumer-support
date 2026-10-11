"""Chat and SSE streaming API routes."""

from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.auth import CurrentDashboardUserDep
from app.core.permissions import EffectivePermissionsDep, forbidden, require_permission
from app.core.rbac import Permission
from app.core.tenant_context import DashboardTenantDep
from app.db.postgres import DbSessionDep
from app.features import mock_services
from app.features.conversations import service as conversation_service
from app.features.schemas import ChatRequest, ChatResponse, MOCK_MESSAGE_ID

router = APIRouter(prefix="/chat", tags=["chat"])


async def authorized_chat_response(
    request: ChatRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
    effective_permissions: EffectivePermissionsDep,
) -> ChatResponse:
    if request.mode == "rag" and Permission.VIEW_DOCUMENTS not in effective_permissions:
        raise forbidden()
    if request.conversation_id is not None:
        conversation = await conversation_service.get_conversation(
            session, tenant.tenant_id, request.conversation_id
        )
        if (
            Permission.VIEW_CONVERSATIONS not in effective_permissions
            and conversation.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": "Conversation was not found."},
            )
    return mock_services.dashboard_chat(
        request,
        include_document_sources=Permission.VIEW_DOCUMENTS in effective_permissions,
        allow_sales_tool={Permission.USE_AGENT_TOOLS, Permission.VIEW_SALES} <= effective_permissions,
    )


AuthorizedChatResponseDep = Annotated[ChatResponse, Depends(authorized_chat_response)]


@router.post("", dependencies=[Depends(require_permission(Permission.USE_DASHBOARD_CHAT))])
async def chat(response: AuthorizedChatResponseDep) -> ChatResponse:
    return response


@router.post(
    "/stream",
    response_class=EventSourceResponse,
    dependencies=[Depends(require_permission(Permission.USE_DASHBOARD_CHAT))],
)
async def stream_chat(
    response: AuthorizedChatResponseDep,
) -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(
        event="message_start",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(MOCK_MESSAGE_ID),
        },
    )
    yield ServerSentEvent(event="token", data={"text": "This is a placeholder "})
    yield ServerSentEvent(event="token", data={"text": "dashboard response."})
    for source in response.sources:
        yield ServerSentEvent(event="source", data=mock_services.sse_payload(source))
    for tool_name in response.used_tools:
        yield ServerSentEvent(event="tool_call", data={"name": tool_name, "status": "started"})
        yield ServerSentEvent(
            event="tool_result", data={"name": tool_name, "status": "completed"}
        )
    yield ServerSentEvent(
        event="message_end",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(response.message.id),
            "used_tools": response.used_tools,
        },
    )
