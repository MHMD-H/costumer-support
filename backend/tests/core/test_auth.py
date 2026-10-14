import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import auth
from app.db.models import User


class StaticJwksClient:
    def __init__(self, public_key) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self.public_key)


@pytest.fixture
def jwt_environment(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setattr(
        auth,
        "get_jwks_client",
        lambda _url: StaticJwksClient(private_key.public_key()),
    )
    return private_key


def make_token(private_key, **overrides: object) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "sub": str(uuid4()),
        "iss": "https://example.supabase.co/auth/v1",
        "aud": "authenticated",
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def assert_unauthorized(token: str) -> None:
    with pytest.raises(HTTPException) as error:
        auth.validate_jwt(token)
    assert error.value.status_code == 401


def test_validate_jwt_returns_subject_only_after_valid_verification(jwt_environment) -> None:
    token = make_token(jwt_environment)

    verified = auth.validate_jwt(token)

    assert verified.subject


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "wrong-audience"},
    ],
)
def test_validate_jwt_rejects_expired_wrong_issuer_and_wrong_audience(jwt_environment, claims) -> None:
    assert_unauthorized(make_token(jwt_environment, **claims))


def test_validate_jwt_rejects_malformed_and_invalidly_signed_tokens(jwt_environment) -> None:
    assert_unauthorized("not-a-jwt")

    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert_unauthorized(make_token(attacker_key))


def test_current_dashboard_user_resolves_the_matching_active_application_user(monkeypatch) -> None:
    auth_user_id = uuid4()
    user = User(
        id=uuid4(),
        tenant_id=uuid4(),
        auth_user_id=auth_user_id,
        is_active=True,
        name="Application User",
        email="user@example.com",
        role="team_member",
    )

    async def get_user(_session, received_auth_user_id):
        assert received_auth_user_id == auth_user_id
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)

    current_user = asyncio.run(
        auth.get_current_dashboard_user(auth.VerifiedSupabaseToken(subject=str(auth_user_id)), None)
    )

    assert current_user.id == user.id
    assert current_user.tenant_id == user.tenant_id
    assert current_user.role == "team_member"


def test_verified_new_user_is_created_unlinked_as_store_owner(jwt_environment, monkeypatch) -> None:
    auth_user_id = uuid4()
    token = make_token(
        jwt_environment,
        sub=str(auth_user_id),
        email="merchant@example.com",
        user_metadata={"role": "admin", "tenant_id": str(uuid4())},
    )
    captured = {}

    async def get_user(_session, received_id):
        assert received_id == auth_user_id
        return None

    async def create_user(_session, **kwargs):
        captured.update(kwargs)
        return User(
            id=uuid4(), tenant_id=None, auth_user_id=kwargs["auth_user_id"],
            is_active=True, name=kwargs["email"], email=kwargs["email"], role="store_owner",
        )

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    monkeypatch.setattr(auth.user_repository, "create_unlinked_store_owner", create_user)

    resolved = asyncio.run(auth.get_current_dashboard_user(auth.validate_jwt(token), None))

    assert captured == {"auth_user_id": auth_user_id, "email": "merchant@example.com"}
    assert resolved.tenant_id is None
    assert resolved.role == "store_owner"


def test_missing_verified_email_cannot_create_application_user(monkeypatch) -> None:
    async def get_user(*_args):
        return None

    async def create_user(*_args, **_kwargs):
        pytest.fail("An application user must not be created without a verified email claim")

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    monkeypatch.setattr(auth.user_repository, "create_unlinked_store_owner", create_user)
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.get_current_dashboard_user(auth.VerifiedSupabaseToken(subject=str(uuid4())), None))
    assert error.value.status_code == 401


@pytest.mark.parametrize("resolved_user", [None, "disabled", "mismatched"])
def test_current_dashboard_user_rejects_unmatched_or_disabled_users(monkeypatch, resolved_user) -> None:
    user = None
    if resolved_user in {"disabled", "mismatched"}:
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            auth_user_id=uuid4(),
            is_active=resolved_user == "mismatched",
            name="Disabled", email="disabled@example.com", role="team_member",
        )

    async def get_user(_session, _auth_user_id):
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            auth.get_current_dashboard_user(auth.VerifiedSupabaseToken(subject=str(uuid4())), None)
        )
    assert error.value.status_code == 401


def test_forged_jwt_metadata_cannot_choose_role_or_tenant(jwt_environment, monkeypatch) -> None:
    auth_user_id, actual_tenant_id = uuid4(), uuid4()
    token = make_token(
        jwt_environment,
        sub=str(auth_user_id),
        user_metadata={"role": "store_owner", "tenant_id": str(uuid4())},
    )
    user = User(
        id=uuid4(), tenant_id=actual_tenant_id, auth_user_id=auth_user_id,
        is_active=True, name="Member", email="member@example.com", role="team_member",
    )

    async def get_user(*_args):
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    resolved = asyncio.run(auth.get_current_dashboard_user(auth.validate_jwt(token), None))
    assert resolved.role == "team_member"
    assert resolved.tenant_id == actual_tenant_id


def test_unknown_stored_role_is_forbidden_after_verified_identity(monkeypatch) -> None:
    auth_user_id = uuid4()
    user = User(
        id=uuid4(), tenant_id=uuid4(), auth_user_id=auth_user_id,
        is_active=True, name="Invalid", email="invalid@example.com", role="super_admin",
    )

    async def get_user(*_args):
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.get_current_dashboard_user(
            auth.VerifiedSupabaseToken(subject=str(auth_user_id)), None
        ))
    assert error.value.status_code == 403
