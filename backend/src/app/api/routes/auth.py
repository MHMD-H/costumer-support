"""Authentication API routes.

Supabase Auth owns dashboard sign-in, sign-up, password resets, sessions, and
sign-out. This router deliberately exposes only application-facing identity
endpoints.
"""

from fastapi import APIRouter

from app.core.auth import CurrentDashboardUserDep
from app.features.schemas import AuthUserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me")
def get_me(current_user: CurrentDashboardUserDep) -> AuthUserResponse:
    return current_user
