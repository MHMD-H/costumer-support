from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.requests import Request

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


def resolve_immediate(coroutine) -> object:
    """Drive the dependency coroutine whose mocked repository completes immediately."""
    with pytest.raises(StopIteration) as result:
        coroutine.send(None)
    return result.value.value


def resolve_current_user(token: auth.VerifiedSupabaseToken) -> object:
    return resolve_immediate(auth.get_current_dashboard_user(token, None))


def test_validate_jwt_returns_subject_only_after_valid_verification(jwt_environment) -> None:
    subject = str(uuid4())
    token = make_token(jwt_environment, sub=subject)

    verified = auth.validate_jwt(token)

    assert verified.subject == subject


def test_validate_jwt_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as error:
        auth.validate_jwt(None)

    assert error.value.status_code == 401


def test_bearer_dependency_accepts_only_a_cryptographically_valid_token(jwt_environment) -> None:
    subject = str(uuid4())
    valid_token = make_token(jwt_environment, sub=subject)
    valid_request = Request({
        "type": "http",
        "headers": [(b"authorization", f"Bearer {valid_token}".encode())],
    })
    invalid_request = Request({
        "type": "http",
        "headers": [(b"authorization", b"Bearer non-empty-but-invalid")],
    })

    valid_dependency_call = auth.oauth2_scheme(valid_request)
    with pytest.raises(StopIteration) as valid_result:
        valid_dependency_call.send(None)
    invalid_dependency_call = auth.oauth2_scheme(invalid_request)
    with pytest.raises(StopIteration) as invalid_result:
        invalid_dependency_call.send(None)

    accepted = auth.validate_jwt(valid_result.value.value)
    rejected = invalid_result.value.value

    assert accepted.subject == subject
    assert rejected == "non-empty-but-invalid"
    assert_unauthorized(rejected)


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

    current_user = resolve_current_user(
        auth.VerifiedSupabaseToken(subject=str(auth_user_id))
    )

    assert current_user.id == user.id
    assert current_user.tenant_id == user.tenant_id
    assert current_user.role == "team_member"


def test_current_dashboard_user_rejects_absent_user_even_with_verified_email(
    jwt_environment, monkeypatch
) -> None:
    auth_user_id = uuid4()
    token = make_token(
        jwt_environment,
        sub=str(auth_user_id),
        email="merchant@example.com",
        user_metadata={"role": "admin", "tenant_id": str(uuid4())},
    )

    async def get_user(_session, received_id):
        assert received_id == auth_user_id
        return None

    async def create_user(*_args, **_kwargs):
        pytest.fail("Authorization must not provision an application user")

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    monkeypatch.setattr(auth.user_repository, "create_unlinked_store_owner", create_user)

    with pytest.raises(HTTPException) as error:
        resolve_current_user(auth.validate_jwt(token))

    assert error.value.status_code == 401


def test_task4_bootstrap_creates_only_an_unlinked_store_owner_from_verified_identity(
    monkeypatch,
) -> None:
    auth_user_id = uuid4()
    created = {}

    async def get_user(_session, received_auth_user_id):
        assert received_auth_user_id == auth_user_id
        return None

    async def create_user(_session, **values):
        created.update(values)
        return User(
            id=uuid4(),
            tenant_id=None,
            auth_user_id=values["auth_user_id"],
            is_active=True,
            name=values["email"],
            email=values["email"],
            role="store_owner",
        )

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    monkeypatch.setattr(auth.user_repository, "create_unlinked_store_owner", create_user)

    resolved = resolve_immediate(
        auth.get_or_create_current_application_user(
            auth.VerifiedSupabaseToken(
                subject=str(auth_user_id), email="Merchant@Example.com"
            ),
            None,
        )
    )

    assert created == {
        "auth_user_id": auth_user_id,
        "email": "merchant@example.com",
    }
    assert resolved.tenant_id is None
    assert resolved.role == "store_owner"


def test_task4_bootstrap_rejects_missing_verified_email_without_creating_user(
    monkeypatch,
) -> None:
    async def get_user(*_args):
        return None

    async def create_user(*_args, **_kwargs):
        pytest.fail("Missing verified email must not create an application user")

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)
    monkeypatch.setattr(auth.user_repository, "create_unlinked_store_owner", create_user)

    with pytest.raises(HTTPException) as error:
        resolve_immediate(
            auth.get_or_create_current_application_user(
                auth.VerifiedSupabaseToken(subject=str(uuid4())), None
            )
        )

    assert error.value.status_code == 401


def test_current_dashboard_user_rejects_disabled_matching_user(monkeypatch) -> None:
    auth_user_id = uuid4()
    user = User(
        id=uuid4(), tenant_id=uuid4(), auth_user_id=auth_user_id,
        is_active=False, name="Disabled", email="disabled@example.com", role="team_member",
    )

    async def get_user(_session, received_auth_user_id):
        assert received_auth_user_id == auth_user_id
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)

    with pytest.raises(HTTPException) as error:
        resolve_current_user(
            auth.VerifiedSupabaseToken(subject=str(auth_user_id))
        )
    assert error.value.status_code == 401


def test_current_dashboard_user_rejects_mismatched_application_user(monkeypatch) -> None:
    auth_user_id = uuid4()
    user = User(
        id=uuid4(), tenant_id=uuid4(), auth_user_id=uuid4(),
        is_active=True, name="Mismatched", email="mismatched@example.com", role="team_member",
    )

    async def get_user(_session, received_auth_user_id):
        assert received_auth_user_id == auth_user_id
        return user

    monkeypatch.setattr(auth.user_repository, "get_user_by_auth_user_id", get_user)

    with pytest.raises(HTTPException) as error:
        resolve_current_user(
            auth.VerifiedSupabaseToken(subject=str(auth_user_id))
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
    resolved = resolve_current_user(auth.validate_jwt(token))
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
        resolve_current_user(auth.VerifiedSupabaseToken(subject=str(auth_user_id)))
    assert error.value.status_code == 403
