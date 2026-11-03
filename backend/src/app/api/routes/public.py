"""Public Shopify widget API routes."""

from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.permissions import (
    PublicWidgetBodyDep,
    PublicWidgetQueryDep,
)
from app.db.postgres import DbSessionDep
from app.features import mock_services, public_widget as public_widget_service
from app.features.schemas import (
    PublicChatResponse,
    PublicWidgetConfigResponse,
)

router = APIRouter(prefix="/public", tags=["public-widget"])


@router.get("/widget/config")
def get_widget_config(
    tenant: PublicWidgetQueryDep,
) -> PublicWidgetConfigResponse:
    return public_widget_service.widget_config(tenant)


@router.post("/chat")
async def public_chat(
    context: PublicWidgetBodyDep,
    session: DbSessionDep,
) -> PublicChatResponse:
    return await public_widget_service.public_chat(session, context)


@router.post("/chat/stream", response_class=EventSourceResponse)
async def stream_public_chat(
    context: PublicWidgetBodyDep,
    session: DbSessionDep,
) -> AsyncIterable[ServerSentEvent]:
    response = await public_widget_service.public_chat(session, context)
    yield ServerSentEvent(
        event="message_start",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(response.message.id),
        },
    )
    yield ServerSentEvent(event="token", data={"text": "This is a placeholder "})
    yield ServerSentEvent(event="token", data={"text": "public response."})
    for source in response.sources:
        yield ServerSentEvent(event="source", data=mock_services.sse_payload(source))
    yield ServerSentEvent(
        event="message_end",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(response.message.id),
        },
    )
