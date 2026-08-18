"""Tests for the documented V1/V2 FastAPI contract."""

from fastapi.testclient import TestClient

from app.features.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackCreateRequest,
    LoginRequest,
    LoginResponse,
    PublicChatRequest,
    PublicChatResponse,
    SearchRequest,
    SearchResponse,
)
from app.main import create_app


DOCUMENTED_ROUTES = {
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/users"),
    ("GET", "/users/{user_id}"),
    ("GET", "/products"),
    ("GET", "/products/{product_id}"),
    ("GET", "/orders"),
    ("GET", "/orders/{order_id}"),
    ("POST", "/sales/summary"),
    ("GET", "/campaigns"),
    ("GET", "/campaigns/{campaign_id}"),
    ("GET", "/documents"),
    ("POST", "/documents"),
    ("GET", "/documents/{document_id}"),
    ("GET", "/documents/{document_id}/chunks"),
    ("GET", "/conversations"),
    ("POST", "/conversations"),
    ("GET", "/conversations/{conversation_id}"),
    ("GET", "/conversations/{conversation_id}/messages"),
    ("POST", "/chat"),
    ("POST", "/chat/stream"),
    ("POST", "/search"),
    ("POST", "/feedback"),
    ("GET", "/agent/tools"),
    ("GET", "/public/widget/config"),
    ("POST", "/public/chat"),
    ("POST", "/public/chat/stream"),
}


def test_app_startup_and_health() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_all_documented_routes_exist() -> None:
    app = create_app()
    existing = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    missing = DOCUMENTED_ROUTES - existing

    assert missing == set()


def test_dashboard_endpoints_require_auth_but_login_is_public() -> None:
    client = TestClient(create_app())

    login = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "password123"},
    )
    me = client.get("/auth/me")
    chat = client.post("/chat", json={"message": "hello"})

    assert login.status_code == 200
    assert me.status_code == 401
    assert chat.status_code == 401


def test_public_widget_endpoints_do_not_require_dashboard_jwt() -> None:
    client = TestClient(create_app())

    config = client.get(
        "/public/widget/config",
        params={
            "shop_domain": "example-store.myshopify.com",
            "widget_public_key": "public-key",
        },
    )
    chat = client.post(
        "/public/chat",
        json={
            "shop_domain": "example-store.myshopify.com",
            "widget_public_key": "public-key",
            "message": "hello",
        },
    )

    assert config.status_code == 200
    assert chat.status_code == 200
    assert "tenant_id" not in chat.json()


def test_schema_examples_validate() -> None:
    login_request = LoginRequest(email="owner@example.com", password="password123")
    public_request = PublicChatRequest(
        shop_domain="example-store.myshopify.com",
        widget_public_key="public-key",
        message="hello",
    )
    dashboard_request = ChatRequest(message="hello", mode="auto")
    feedback_request = FeedbackCreateRequest(
        conversation_id="33333333-3333-3333-3333-333333333333",
        message_id="44444444-4444-4444-4444-444444444444",
        rating=5,
    )

    client = TestClient(create_app())
    login_response = client.post(
        "/auth/login",
        json=login_request.model_dump(mode="json"),
    )
    public_response = client.post(
        "/public/chat",
        json=public_request.model_dump(mode="json"),
    )
    dashboard_response = client.post(
        "/chat",
        headers={"Authorization": "Bearer test-token"},
        json=dashboard_request.model_dump(mode="json"),
    )
    search_response = client.post(
        "/search",
        headers={"Authorization": "Bearer test-token"},
        json=SearchRequest(query="returns").model_dump(mode="json"),
    )

    LoginResponse.model_validate(login_response.json())
    PublicChatResponse.model_validate(public_response.json())
    ChatResponse.model_validate(dashboard_response.json())
    SearchResponse.model_validate(search_response.json())
    assert feedback_request.rating == 5
