"""Chat and SSE streaming API routes."""

from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import DashboardTenantDep
from app.features import mock_services
from app.features.schemas import ChatRequest, ChatResponse, MOCK_MESSAGE_ID

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
def chat(
    request: ChatRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> ChatResponse:
    return mock_services.dashboard_chat(request)


@router.post("/stream", response_class=EventSourceResponse)
async def stream_chat(
    request: ChatRequest,
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
) -> AsyncIterable[ServerSentEvent]:
    response = mock_services.dashboard_chat(request)
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
    yield ServerSentEvent(event="tool_call", data={"name": "get_sales", "status": "started"})
    yield ServerSentEvent(
        event="tool_result",
        data={"name": "get_sales", "status": "completed"},
    )
    yield ServerSentEvent(
        event="message_end",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(response.message.id),
            "used_tools": response.used_tools,
        },
    )
