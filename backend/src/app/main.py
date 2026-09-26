"""FastAPI app entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import (
    agent,
    auth,
    campaigns,
    chat,
    conversations,
    documents,
    feedback,
    orders,
    permissions,
    products,
    public,
    sales,
    search,
    shopify,
    tenants,
    users,
)
from app.core.exceptions import add_exception_handlers
from app.db.postgres import dispose_engine, validate_database_connection


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await validate_database_connection()
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Commerce Copilot API",
        version="0.1.0",
        summary="V1/V2 API foundation for the dashboard and Shopify widget.",
        description=(
            "Protected dashboard APIs require placeholder Supabase JWT validation. "
            "Public widget APIs use placeholder store/widget validation."
        ),
        lifespan=lifespan,
    )

    add_exception_handlers(app)
    app.include_router(auth.router)
    app.include_router(shopify.router)
    app.include_router(users.router)
    app.include_router(tenants.router)
    app.include_router(permissions.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(sales.router)
    app.include_router(campaigns.router)
    app.include_router(documents.router)
    app.include_router(conversations.router)
    app.include_router(chat.router)
    app.include_router(search.router)
    app.include_router(feedback.router)
    app.include_router(agent.router)
    app.include_router(public.router)

    # TODO: Add GET /tenants/{tenant_id}/statistics with aggregate COUNT/SUM/AVG
    # queries instead of loading related rows.
    # TODO: Add GET /users/{user_id}/history with pagination for large collections
    # such as orders, documents, conversations, and feedback.
    # TODO: Add /reports/sales for Shopify-sourced sales reports; sales stay
    # read-only from the dashboard.
    # TODO: Add GET /conversations/{conversation_id}/analysis and load messages
    # and feedback only for that explicit analysis endpoint.

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
