"""Security tests for the unauthenticated Shopify storefront widget."""

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.permissions import PUBLIC_WIDGET_RATE_LIMITER
from app.db.postgres import get_db_session
from app.db.repositories import products as product_repository
from app.db.repositories import tenants as tenant_repository
from app.features.public_widget import (
    MAX_PUBLIC_WIDGET_BODY_BYTES,
    PublicWidgetBodyLimitMiddleware,
)
from app.main import create_app


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT_ID = UUID("22222222-2222-2222-2222-222222222222")
SHOP_DOMAIN = "merchant.myshopify.com"
ORIGIN = "https://shop.example.com"
WIDGET_KEY = "public-widget-key"


def tenant_record(**updates):
    values = {
        "id": TENANT_ID,
        "name": "Merchant Store",
        "shop_id": "gid://shopify/Shop/1",
        "shop_domain": SHOP_DOMAIN,
        "widget_enabled": True,
        "widget_allowed_origins": [ORIGIN],
        "widget_settings": {
            "greeting": "How can we help?",
            "theme": {"primary_color": "#008060", "private_note": "do not expose"},
            "orders": ["private"],
        },
    }
    values.update(updates)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def reset_public_rate_limiter():
    PUBLIC_WIDGET_RATE_LIMITER.reset()
    yield
    PUBLIC_WIDGET_RATE_LIMITER.reset()


@pytest.fixture
def widget_client(monkeypatch) -> TestClient:
    async def fake_db_session():
        yield None

    async def resolve_tenant(_session, *, shop_id, shop_domain, widget_public_key):
        if (
            widget_public_key == WIDGET_KEY
            and (shop_id is None or shop_id == "gid://shopify/Shop/1")
            and (shop_domain is None or shop_domain == SHOP_DOMAIN)
        ):
            return tenant_record()
        return None

    monkeypatch.setattr(tenant_repository, "get_enabled_public_widget_tenant", resolve_tenant)
    app = create_app()
    app.dependency_overrides[get_db_session] = fake_db_session
    return TestClient(app)


def config_request(client: TestClient, **params):
    values = {"shop_domain": SHOP_DOMAIN, "widget_public_key": WIDGET_KEY}
    values.update(params)
    return client.get(
        "/public/widget/config",
        params=values,
        headers={"Origin": ORIGIN},
    )


def chat_request(client: TestClient, **payload):
    values = {
        "shop_domain": SHOP_DOMAIN,
        "widget_public_key": WIDGET_KEY,
        "message": "Do you ship internationally?",
    }
    values.update(payload)
    return client.post(
        "/public/chat",
        json=values,
        headers={"Origin": ORIGIN},
    )


def test_valid_widget_mapping_returns_only_allowlisted_config(widget_client) -> None:
    response = config_request(widget_client)

    assert response.status_code == 200
    assert response.json() == {
        "shop_id": "gid://shopify/Shop/1",
        "shop_domain": SHOP_DOMAIN,
        "store_name": "Merchant Store",
        "widget_enabled": True,
        "greeting": "How can we help?",
        "theme": {"primary_color": "#008060"},
    }
    assert "tenant_id" not in response.text
    assert "private_note" not in response.text
    assert "orders" not in response.text


@pytest.mark.parametrize(
    "params",
    [
        {"shop_domain": "other.myshopify.com"},
        {"widget_public_key": "wrong-key"},
        {"shop_id": "gid://shopify/Shop/2"},
    ],
)
def test_invalid_store_or_widget_mapping_is_rejected(widget_client, params) -> None:
    response = config_request(widget_client, **params)

    assert response.status_code == 403
    assert response.json()["message"] == "Widget access is invalid."
    assert "tenant_id" not in response.text


def test_missing_store_identity_is_rejected(widget_client) -> None:
    response = widget_client.get(
        "/public/widget/config",
        params={"widget_public_key": WIDGET_KEY},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("origin", [None, "https://attacker.example", "null", "http://shop.example.com"])
def test_missing_or_disallowed_origin_is_rejected(widget_client, origin) -> None:
    headers = {"Origin": origin} if origin is not None else {}
    response = widget_client.get(
        "/public/widget/config",
        params={"shop_domain": SHOP_DOMAIN, "widget_public_key": WIDGET_KEY},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Storefront origin is not allowed."


def test_rate_limit_exhaustion_returns_429(widget_client, monkeypatch) -> None:
    monkeypatch.setattr(PUBLIC_WIDGET_RATE_LIMITER, "request_limit", 2)

    assert config_request(widget_client).status_code == 200
    assert config_request(widget_client).status_code == 200
    response = config_request(widget_client)

    assert response.status_code == 429
    assert response.json()["error"] == "rate_limited"


@pytest.mark.parametrize("path", ["/public/chat", "/public/chat/stream"])
def test_oversized_public_chat_body_is_rejected_before_dependencies(monkeypatch, path) -> None:
    async def must_not_resolve(*_args, **_kwargs):
        raise AssertionError("oversized body reached tenant resolution")

    monkeypatch.setattr(tenant_repository, "get_enabled_public_widget_tenant", must_not_resolve)
    client = TestClient(create_app())

    response = client.post(
        path,
        content=b"x" * (MAX_PUBLIC_WIDGET_BODY_BYTES + 1),
        headers={"Content-Type": "application/json", "X-Request-Id": "oversized-request"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "error": "payload_too_large",
        "message": "Public chat request exceeds the size limit.",
        "details": [],
        "request_id": "oversized-request",
    }


def test_public_body_limit_counts_actual_chunks_without_content_length() -> None:
    downstream_called = False
    sent = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"x" * 20_000, "more_body": True},
            {"type": "http.request", "body": b"x" * 20_000, "more_body": False},
        ]
    )

    async def downstream(_scope, _receive, _send):
        nonlocal downstream_called
        downstream_called = True

    async def receive():
        return next(chunks)

    async def send(message):
        sent.append(message)

    asyncio.run(
        PublicWidgetBodyLimitMiddleware(downstream)(
            {
                "type": "http",
                "method": "POST",
                "path": "/public/chat",
                "headers": [(b"content-length", b"0")],
            },
            receive,
            send,
        )
    )

    assert downstream_called is False
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_oversized_public_chat_handles_non_utf8_request_id() -> None:
    sent = []

    async def downstream(_scope, _receive, _send):
        raise AssertionError("oversized body reached downstream app")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(
        PublicWidgetBodyLimitMiddleware(downstream)(
            {
                "type": "http",
                "method": "POST",
                "path": "/public/chat",
                "headers": [
                    (b"content-length", str(MAX_PUBLIC_WIDGET_BODY_BYTES + 1).encode()),
                    (b"x-request-id", b"\xff"),
                ],
            },
            receive,
            send,
        )
    )

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_public_chat_body_replay_preserves_later_disconnect() -> None:
    received = []
    incoming = iter(
        [
            {"type": "http.request", "body": b"{}", "more_body": False},
            {"type": "http.disconnect"},
        ]
    )

    async def downstream(_scope, receive, _send):
        received.append(await receive())
        received.append(await receive())

    async def receive():
        return next(incoming)

    async def send(_message):
        return None

    asyncio.run(
        PublicWidgetBodyLimitMiddleware(downstream)(
            {
                "type": "http",
                "method": "POST",
                "path": "/public/chat/stream",
                "headers": [],
            },
            receive,
            send,
        )
    )

    assert received == [
        {"type": "http.request", "body": b"{}", "more_body": False},
        {"type": "http.disconnect"},
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("shop_id", "s" * 257),
        ("shop_domain", "d" * 254),
        ("widget_public_key", "k" * 257),
        ("message", "m" * 4_001),
        ("page_url", "u" * 2_049),
        ("product_id", "p" * 257),
    ],
)
def test_overlong_public_chat_fields_are_rejected(widget_client, field, value) -> None:
    response = chat_request(widget_client, **{field: value})

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_overlong_widget_config_query_is_rejected(widget_client) -> None:
    response = config_request(widget_client, widget_public_key="k" * 257)

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


@pytest.mark.parametrize("product_id", ["private-product", "other-tenant-product"])
def test_private_or_cross_tenant_product_context_is_not_found(
    widget_client, monkeypatch, product_id
) -> None:
    async def no_public_product(_session, tenant_id, external_product_id):
        assert tenant_id == TENANT_ID
        assert external_product_id == product_id
        return None

    monkeypatch.setattr(product_repository, "get_public_product_by_external_id", no_public_product)

    response = chat_request(widget_client, product_id=product_id)

    assert response.status_code == 404
    assert response.json()["message"] == "Product was not found."
    assert "tenant_id" not in response.text


def test_public_same_tenant_product_context_is_allowed(widget_client, monkeypatch) -> None:
    async def public_product(_session, tenant_id, external_product_id):
        assert tenant_id == TENANT_ID
        assert external_product_id == "public-product"
        return SimpleNamespace(id=UUID("33333333-3333-3333-3333-333333333333"))

    monkeypatch.setattr(product_repository, "get_public_product_by_external_id", public_product)

    response = chat_request(widget_client, product_id="public-product")

    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_public_chat_response_contains_no_unverified_sources_or_internal_data(widget_client) -> None:
    response = chat_request(widget_client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == []
    assert payload["message"]["sources"] == []
    serialized = response.text.lower()
    for forbidden in ("tenant_id", "orders", "sales", "campaigns", "agent_tools", "internal"):
        assert forbidden not in serialized
