"""Customer-safe public Shopify widget use cases."""

from collections import deque
import re

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import PublicWidgetChatContext
from app.core.tenant_context import TenantContext
from app.db.repositories import products as product_repository
from app.features.schemas import (
    PublicChatMessage,
    PublicChatResponse,
    PublicWidgetConfigResponse,
    new_uuid,
    now_utc,
)

PUBLIC_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_PUBLIC_WIDGET_BODY_BYTES = 32 * 1024
PUBLIC_WIDGET_BODY_PATHS = frozenset({"/public/chat", "/public/chat/stream"})


class PublicWidgetBodyLimitMiddleware:
    """Reject oversized public chat bodies before JSON parsing or dependencies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "").rstrip("/")
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or path not in PUBLIC_WIDGET_BODY_PATHS
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        response = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={
                "error": "payload_too_large",
                "message": "Public chat request exceeds the size limit.",
                "details": [],
                "request_id": headers.get(b"x-request-id", b"").decode("latin-1") or None,
            },
        )
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > MAX_PUBLIC_WIDGET_BODY_BYTES:
            await response(scope, receive, send)
            return

        total = 0
        messages = deque()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                return
            total += len(message.get("body", b""))
            if total > MAX_PUBLIC_WIDGET_BODY_BYTES:
                await response(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive():
            if messages:
                return messages.popleft()
            return await receive()

        await self.app(scope, replay_receive, send)


def widget_config(tenant: TenantContext) -> PublicWidgetConfigResponse:
    settings = tenant.widget_settings or {}
    greeting_value = settings.get("greeting")
    greeting = greeting_value[:500] if isinstance(greeting_value, str) else None

    theme: dict[str, str] = {}
    theme_value = settings.get("theme")
    if isinstance(theme_value, dict):
        primary_color = theme_value.get("primary_color")
        if isinstance(primary_color, str) and PUBLIC_COLOR_PATTERN.fullmatch(primary_color):
            theme["primary_color"] = primary_color

    return PublicWidgetConfigResponse(
        shop_id=tenant.shop_id,
        shop_domain=tenant.shop_domain or "",
        store_name=tenant.store_name or "Store",
        widget_enabled=True,
        greeting=greeting,
        theme=theme,
    )


async def public_chat(
    session: AsyncSession, context: PublicWidgetChatContext
) -> PublicChatResponse:
    """Return the safe placeholder response after validating optional product context."""
    if context.request.product_id:
        product = await product_repository.get_public_product_by_external_id(
            session,
            context.tenant.tenant_id,
            context.request.product_id,
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "message": "Product was not found."},
            )

    conversation_id = context.request.conversation_id or new_uuid()
    message = PublicChatMessage(
        id=new_uuid(),
        sender="assistant",
        content="This is a placeholder customer-safe response.",
        sources=[],
        created_at=now_utc(),
    )
    return PublicChatResponse(
        conversation_id=conversation_id,
        message=message,
        sources=[],
    )
