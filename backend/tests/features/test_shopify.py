"""Focused tests for the server-side Shopify connection flow."""

from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
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


def callback_parameters(
    state: str, shop_domain: str = "merchant.myshopify.com"
) -> list[tuple[str, str]]:
    parameters = [
        ("code", "authorization-code"),
        ("shop", shop_domain),
        ("state", state),
        ("timestamp", "1700000000"),
    ]
    message = "&".join(f"{key}={value}" for key, value in sorted(parameters))
    signature = shopify.hmac.new(
        b"test-client-secret", message.encode(), shopify.sha256
    ).hexdigest()
    return [*parameters, ("hmac", signature)]


def resolve_immediate(coroutine):
    """Drive mocked async service calls that complete without yielding."""
    with pytest.raises(StopIteration) as result:
        coroutine.send(None)
    return result.value.value


def test_callback_hmac_rejects_tampering(shopify_environment) -> None:
    parameters = callback_parameters("state-value")
    assert shopify.is_valid_callback_hmac(parameters)
    assert not shopify.is_valid_callback_hmac(
        [("code", "changed"), *parameters[1:]]
    )


def test_complete_connection_rejects_invalid_hmac_before_state_or_exchange(
    shopify_environment, monkeypatch
) -> None:
    async def unexpected(*_args, **_kwargs):
        pytest.fail("Invalid HMAC must be rejected before state use or token exchange")

    monkeypatch.setattr(shopify.shopify_repository, "consume_oauth_state", unexpected)
    monkeypatch.setattr(shopify, "exchange_code_for_access_token", unexpected)
    parameters = callback_parameters("state-value")
    tampered_parameters = [("code", "tampered-code"), *parameters[1:]]

    with pytest.raises(HTTPException) as error:
        resolve_immediate(
            shopify.complete_connection(
                None,
                state="state-value",
                callback_shop_domain="merchant.myshopify.com",
                code="tampered-code",
                callback_parameters=tampered_parameters,
            )
        )

    assert error.value.status_code == 400


def test_begin_connection_hashes_state_before_persistence(shopify_environment, monkeypatch) -> None:
    captured = {}
    user = User(
        id=uuid4(), tenant_id=None, auth_user_id=uuid4(), is_active=True,
        name="Merchant", email="merchant@example.com", role="store_owner",
    )

    async def create_oauth_state(_session, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(shopify.shopify_repository, "create_oauth_state", create_oauth_state)
    authorization_url = resolve_immediate(
        shopify.begin_connection(None, user=user, shop_domain="merchant.myshopify.com")
    )

    state = parse_qs(urlparse(authorization_url).query)["state"][0]
    assert captured["user_id"] == user.id
    assert captured["state_hash"] == shopify.state_hash(state)
    assert captured["state_hash"] != state
    assert captured["shop_domain"] == "merchant.myshopify.com"


def test_token_exchange_requests_expiring_token_without_logging_it(
    shopify_environment, monkeypatch, caplog
) -> None:
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "access_token": "shopify-access-token",
                "refresh_token": "shopify-refresh-token",
            }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(shopify.httpx, "AsyncClient", lambda **_kwargs: Client())

    token = resolve_immediate(
        shopify.exchange_code_for_access_token(
            "merchant.myshopify.com", "authorization-code"
        )
    )

    assert token == "shopify-access-token"
    assert captured["data"]["expiring"] == "1"
    assert "shopify-access-token" not in caplog.text
    assert "shopify-refresh-token" not in caplog.text


def test_canonical_shop_identity_comes_from_graphql(shopify_environment, monkeypatch) -> None:
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "shop": {
                        "id": "gid://shopify/Shop/987654",
                        "name": "Canonical Store",
                        "myshopifyDomain": "canonical.myshopify.com",
                    }
                }
            }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(shopify.httpx, "AsyncClient", lambda **_kwargs: Client())

    identity = resolve_immediate(
        shopify.fetch_canonical_shop(
            "merchant.myshopify.com", "transient-access-token"
        )
    )

    assert identity == (
        "gid://shopify/Shop/987654",
        "canonical.myshopify.com",
        "Canonical Store",
    )
    assert captured["url"].endswith("/graphql.json")
    assert "shop { id name myshopifyDomain }" in captured["json"]["query"]


@pytest.mark.parametrize(("role", "active"), [("team_member", True), ("store_owner", False)])
def test_begin_connection_requires_active_store_owner(
    shopify_environment, monkeypatch, role, active
) -> None:
    user = User(
        id=uuid4(), tenant_id=None, auth_user_id=uuid4(), is_active=active,
        name="Merchant", email="merchant@example.com", role=role,
    )

    async def create_oauth_state(*_args, **_kwargs):
        pytest.fail("Unauthorized user must not create OAuth state")

    monkeypatch.setattr(shopify.shopify_repository, "create_oauth_state", create_oauth_state)
    with pytest.raises(HTTPException) as error:
        resolve_immediate(shopify.begin_connection(None, user=user, shop_domain="merchant.myshopify.com"))
    assert error.value.status_code == 403


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
        resolve_immediate(
            shopify.complete_connection(
                None,
                state=state,
                callback_shop_domain="merchant.myshopify.com",
                code="authorization-code",
                callback_parameters=callback_parameters(state),
            )
        )

    assert error.value.status_code == 400


@pytest.mark.parametrize("failure", ["expired", "reused", "mismatched"])
def test_complete_connection_rejects_unusable_state_before_exchange(
    shopify_environment, monkeypatch, failure
) -> None:
    state = "state-value"
    callback_shop = (
        "different.myshopify.com" if failure == "mismatched" else "merchant.myshopify.com"
    )

    async def consume_state(_session, *, state_hash, shop_domain, consumed_at):
        assert state_hash == shopify.state_hash(state)
        assert shop_domain == callback_shop
        assert consumed_at.tzinfo is not None
        return None

    async def exchange(*_args, **_kwargs):
        pytest.fail("An unusable state must be rejected before code exchange")

    monkeypatch.setattr(shopify.shopify_repository, "consume_oauth_state", consume_state)
    monkeypatch.setattr(shopify, "exchange_code_for_access_token", exchange)

    with pytest.raises(HTTPException) as error:
        resolve_immediate(
            shopify.complete_connection(
                None,
                state=state,
                callback_shop_domain=callback_shop,
                code="authorization-code",
                callback_parameters=callback_parameters(state, callback_shop),
            )
        )

    assert error.value.status_code == 400


def test_complete_connection_uses_canonical_identity_without_persisting_token(
    shopify_environment, monkeypatch, caplog
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
        return SimpleNamespace(
            user_id=user.id,
            shop_domain="merchant.myshopify.com",
            consumed_at=datetime.now(timezone.utc),
        )

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

    resolve_immediate(
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
    assert all("token" not in key for key in captured["connection"])
    assert "shopify-access-token" not in caplog.text


def test_callback_rechecks_stored_owner_before_tenant_or_token_write(
    shopify_environment, monkeypatch
) -> None:
    state = "state-value"
    user = User(
        id=uuid4(), tenant_id=None, auth_user_id=uuid4(), is_active=True,
        name="Merchant", email="merchant@example.com", role="store_owner",
    )

    class Transaction:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return False

    class Session:
        def begin(self):
            return Transaction()

    async def consume_state(*_args, **_kwargs):
        return SimpleNamespace(user_id=user.id)

    async def exchange(*_args, **_kwargs):
        return "shopify-access-token"

    async def canonical_shop(*_args, **_kwargs):
        return "987654", "canonical.myshopify.com", "Canonical Store"

    async def get_user(*_args, **_kwargs):
        user.role = "team_member"
        return user

    async def unexpected_write(*_args, **_kwargs):
        pytest.fail("Revoked owner authority must prevent tenant and token writes")

    monkeypatch.setattr(shopify.shopify_repository, "consume_oauth_state", consume_state)
    monkeypatch.setattr(shopify, "exchange_code_for_access_token", exchange)
    monkeypatch.setattr(shopify, "fetch_canonical_shop", canonical_shop)
    monkeypatch.setattr(shopify.shopify_repository, "get_user", get_user)
    monkeypatch.setattr(shopify.shopify_repository, "create_tenant", unexpected_write)
    monkeypatch.setattr(shopify.shopify_repository, "create_connection", unexpected_write)

    with pytest.raises(HTTPException) as error:
        resolve_immediate(shopify.complete_connection(
            Session(), state=state, callback_shop_domain="merchant.myshopify.com",
            code="authorization-code", callback_parameters=callback_parameters(state),
        ))
    assert error.value.status_code == 403
