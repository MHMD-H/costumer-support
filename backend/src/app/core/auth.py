"""Authentication dependencies.

Current status: placeholder bearer-token validation only.
Why placeholder: local/mock protected-route tests need authentication gates
before real dashboard sessions are wired.
Replace when: dashboard auth moves from local/mock testing to real user sessions.
Target implementation: Supabase JWT verification plus DB-backed user and tenant
lookup.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.features.schemas import (
    AuthUserResponse,
    MOCK_TENANT_ID,
    MOCK_USER_ID,
)


def validate_jwt(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    """Placeholder Supabase JWT validation hook."""
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Dashboard authentication is required.",
            },
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": "Bearer token is invalid."},
        )
    return token


def get_current_dashboard_user(token: Annotated[str, Depends(validate_jwt)]) -> AuthUserResponse:
    return AuthUserResponse(
        id=MOCK_USER_ID,
        tenant_id=MOCK_TENANT_ID,
        name="Mock Dashboard User",
        email="owner@example.com",
        role="store_owner",
    )


JwtDep = Annotated[str, Depends(validate_jwt)]
CurrentDashboardUserDep = Annotated[AuthUserResponse, Depends(get_current_dashboard_user)]
