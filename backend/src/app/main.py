"""FastAPI app entry point."""

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
    tenants,
    users,
)
from app.core.exceptions import add_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Commerce Copilot API",
        version="0.1.0",
        summary="V1/V2 API foundation for the dashboard and Shopify widget.",
        description=(
            "Protected dashboard APIs require placeholder Supabase JWT validation. "
            "Public widget APIs use placeholder store/widget validation."
        ),
    )

    add_exception_handlers(app)
    app.include_router(auth.router)
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

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
