"""Supabase JWT verification dependencies."""

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWKClient

from app.db.postgres import DbSessionDep
from app.db.repositories import users as user_repository
from app.features.schemas import AuthUserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
ALLOWED_JWT_ALGORITHMS = frozenset({"RS256", "ES256", "EdDSA"})


@dataclass(frozen=True)
class VerifiedSupabaseToken:
    """Claims trusted after complete Supabase JWT verification."""

    subject: str


def unauthorized(message: str = "Dashboard authentication is required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "unauthorized", "message": message},
    )


def get_supabase_url() -> str:
    """Return the configured Supabase project URL without a trailing slash."""
    url = getenv("SUPABASE_URL", "").rstrip("/")
    if not url.startswith("https://"):
        raise unauthorized()
    return url


@lru_cache(maxsize=1)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Cache Supabase's public-key client for its short default JWKS lifetime."""
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


def validate_jwt(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> VerifiedSupabaseToken:
    """Extract and cryptographically verify a Supabase access token."""
    if not token:
        raise unauthorized()

    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm not in ALLOWED_JWT_ALGORITHMS:
            raise jwt.InvalidAlgorithmError("Unsupported signing algorithm")

        supabase_url = get_supabase_url()
        signing_key = get_jwks_client(
            f"{supabase_url}/auth/v1/.well-known/jwks.json"
        ).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=getenv("SUPABASE_JWT_AUDIENCE", "authenticated"),
            issuer=f"{supabase_url}/auth/v1",
            options={"require": ["aud", "exp", "iss", "sub"]},
        )
    except (jwt.PyJWTError, ValueError):
        raise unauthorized("Bearer token is invalid.") from None

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise unauthorized("Bearer token is invalid.")
    return VerifiedSupabaseToken(subject=subject)


async def get_current_dashboard_user(
    verified_token: Annotated[VerifiedSupabaseToken, Depends(validate_jwt)],
    session: DbSessionDep,
) -> AuthUserResponse:
    """Resolve the verified Supabase subject to an active application user."""
    try:
        auth_user_id = UUID(verified_token.subject)
    except ValueError:
        raise unauthorized("Bearer token is invalid.") from None

    user = await user_repository.get_user_by_auth_user_id(session, auth_user_id)
    if user is None or not user.is_active or user.auth_user_id != auth_user_id:
        raise unauthorized()

    return AuthUserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


JwtDep = Annotated[VerifiedSupabaseToken, Depends(validate_jwt)]
CurrentUser = AuthUserResponse
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_dashboard_user)]
# Keep the existing route dependency name while exposing the canonical trusted
# request-context name for new consumers.
CurrentDashboardUserDep = CurrentUserDep
