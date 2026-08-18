"""Public Shopify widget API routes."""

from collections.abc import AsyncIterable

from fastapi import APIRouter, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.permissions import (
    PublicWidgetBodyDep,
    PublicWidgetQueryDep,
)
from app.features import mock_services
from app.features.schemas import (
    MOCK_MESSAGE_ID,
    PublicChatRequest,
    PublicChatResponse,
    PublicWidgetConfigResponse,
)

router = APIRouter(prefix="/public", tags=["public-widget"])


@router.get("/widget/config")
def get_widget_config(
    tenant: PublicWidgetQueryDep,
    shop_id: str | None = Query(default=None),
    shop_domain: str | None = Query(default=None),
    widget_public_key: str = Query(),
) -> PublicWidgetConfigResponse:
    return mock_services.widget_config(shop_id, shop_domain)


@router.post("/chat")
def public_chat(
    context: PublicWidgetBodyDep,
) -> PublicChatResponse:
    return mock_services.public_chat(context.request)


@router.post("/chat/stream", response_class=EventSourceResponse)
async def stream_public_chat(
    context: PublicWidgetBodyDep,
) -> AsyncIterable[ServerSentEvent]:
    response = mock_services.public_chat(context.request)
    yield ServerSentEvent(
        event="message_start",
        data={
            "conversation_id": str(response.conversation_id),
            "message_id": str(MOCK_MESSAGE_ID),
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
