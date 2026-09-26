"""Tests for chat API routes."""

from fastapi.testclient import TestClient

from app.core.auth import get_current_dashboard_user
from app.db.postgres import get_db_session
from app.features.mock_services import mock_auth_user
from app.main import create_app


async def fake_db_session():
    yield None


def test_dashboard_stream_returns_sse_events() -> None:
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = mock_auth_user
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chat/stream",
        headers={"Authorization": "Bearer test-token"},
        json={"message": "Show sales", "mode": "agent"},
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message_start" in body
    assert "event: token" in body
    assert "event: source" in body
    assert "event: tool_call" in body
    assert "event: tool_result" in body
    assert "event: message_end" in body


def test_public_stream_returns_customer_safe_sse_events() -> None:
    client = TestClient(create_app())

    with client.stream(
        "POST",
        "/public/chat/stream",
        json={
            "shop_domain": "example-store.myshopify.com",
            "widget_public_key": "public-key",
            "message": "Do you ship internationally?",
        },
    ) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message_start" in body
    assert "event: token" in body
    assert "event: source" in body
    assert "event: message_end" in body
    assert "event: tool_call" not in body
    assert "event: tool_result" not in body


def test_conversation_list_rejects_an_invalid_cursor() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = fake_db_session
    app.dependency_overrides[get_current_dashboard_user] = mock_auth_user
    client = TestClient(app)

    response = client.get(
        "/conversations?cursor=not-a-valid-cursor",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Cursor is invalid."
