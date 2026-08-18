"""Tests for chat API routes."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_dashboard_stream_returns_sse_events() -> None:
    client = TestClient(create_app())

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
