"""Focused tests for the server-side Shopify connection flow."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.tenant_context import resolve_dashboard_tenant
from app.db.models import User
from app.features import shopify
from app.features.schemas import AuthUserResponse


@pytest.fixture
def shopify_environment(monkeypatch):
    monkeypatch.setenv("SHOPIFY_API_KEY", "test-client-id")
    monkeypatch.setenv("SHOPIFY_API_SECRET", "test-client-secret")
    monkeypatch.setenv("SHOPIFY_OAUTH_REDIRECT_URI", "https://api.example.test/shopify/callback")
    monkeypatch.setenv("SHOPIFY_SCOPES", "read_products")
    monkeypatch.setenv("SHOPIFY_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())


def callback_parameters(state: str) -> list[tuple[str, str]]:
    parameters = [
        ("code", "authorization-code"),
        ("shop", "merchant.myshopify.com"),
        ("state", state),
        ("timestamp", "1700000000"),
    ]
    message = "&".join(f"{key}={value}" for key, value in sorted(parameters))
    signature = shopify.hmac.new(
        b"test-client-secret", message.encode(), shopify.sha256
    ).hexdigest()
    return [*parameters, ("hmac", signature)]


def test_callback_hmac_rejects_tampering(shopify_environment) -> None:
    parameters = callback_parameters("state-value")
    assert shopify.is_valid_callback_hmac(parameters)
    assert not shopify.is_valid_callback_hmac(
        [("code", "changed"), *parameters[1:]]
    )


def test_begin_connection_hashes_state_before_persistence(shopify_environment, monkeypatch) -> None:
    captured = {}
    user = User(
        id=uuid4(), tenant_id=None, auth_user_id=uuid4(), is_active=True,
        name="Merchant", email="merchant@example.com", role="store_owner",
    )

    async def create_oauth_state(_session, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(shopify.shopify_repository, "create_oauth_state", create_oauth_state)
    authorization_url = asyncio.run(
        shopify.begin_connection(None, user=user, shop_domain="merchant.myshopify.com")
    )

    state = parse_qs(urlparse(authorization_url).query)["state"][0]
    assert captured["user_id"] == user.id
    assert captured["state_hash"] == shopify.state_hash(state)
    assert captured["state_hash"] != state


def test_unlinked_user_cannot_access_tenant_dashboard() -> None:
    user = AuthUserResponse(
        id=uuid4(), tenant_id=None, name="Merchant", email="merchant@example.com", role="store_owner"
    )

    with pytest.raises(HTTPException) as error:
        resolve_dashboard_tenant(user)

    assert error.value.status_code == 403


def test_complete_connection_rejects_invalid_or_consumed_state(shopify_environment, monkeypatch) -> None:
    state = "state-value"

    async def consume_state(*_args, **_kwargs):
        return None

    monkeypatch.setattr(shopify.shopify_repository, "consume_oauth_state", consume_state)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            shopify.complete_connection(
                None,
                state=state,
                callback_shop_domain="merchant.myshopify.com",
                code="authorization-code",
                callback_parameters=callback_parameters(state),
            )
        )

    assert error.value.status_code == 400


def test_complete_connection_uses_canonical_identity_and_encrypts_token(
    shopify_environment, monkeypatch
) -> None:
    state = "state-value"
    user = User(
        id=uuid4(), tenant_id=None, auth_user_id=uuid4(), is_active=True,
        name="Merchant", email="merchant@example.com", role="store_owner",
    )
    captured = {}

    class Transaction:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return False

    class Session:
        def begin(self):
            return Transaction()

    async def consume_state(*_args, **_kwargs):
        return SimpleNamespace(user_id=user.id, consumed_at=datetime.now(timezone.utc))

    async def exchange(*_args, **_kwargs):
        return "shopify-access-token"

    async def canonical_shop(*_args, **_kwargs):
        return "987654", "canonical.myshopify.com", "Canonical Store"

    async def get_user(*_args, **_kwargs):
        return user

    async def get_connection(*_args, **_kwargs):
        return None

    async def create_tenant(_session, **kwargs):
        captured["tenant"] = kwargs
        return SimpleNamespace(id=uuid4())

    async def create_connection(_session, **kwargs):
        captured["connection"] = kwargs

    monkeypatch.setattr(shopify.shopify_repository, "consume_oauth_state", consume_state)
    monkeypatch.setattr(shopify, "exchange_code_for_access_token", exchange)
    monkeypatch.setattr(shopify, "fetch_canonical_shop", canonical_shop)
    monkeypatch.setattr(shopify.shopify_repository, "get_user", get_user)
    monkeypatch.setattr(shopify.shopify_repository, "get_connection_by_shop_id", get_connection)
    monkeypatch.setattr(shopify.shopify_repository, "get_connection_by_tenant_id", get_connection)
    monkeypatch.setattr(shopify.shopify_repository, "create_tenant", create_tenant)
    monkeypatch.setattr(shopify.shopify_repository, "create_connection", create_connection)

    asyncio.run(
        shopify.complete_connection(
            Session(),
            state=state,
            callback_shop_domain="merchant.myshopify.com",
            code="authorization-code",
            callback_parameters=callback_parameters(state),
        )
    )

    assert captured["tenant"]["shop_id"] == "987654"
    assert captured["tenant"]["shop_domain"] == "canonical.myshopify.com"
    assert captured["connection"]["shop_domain"] == "canonical.myshopify.com"
    assert "shopify-access-token" not in captured["connection"]["access_token_encrypted"]
