"""Authentication API routes."""

from fastapi import APIRouter, Response, status

from app.core.auth import CurrentDashboardUserDep
from app.features import mock_services
from app.features.schemas import AuthUserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: LoginRequest) -> LoginResponse:
    return mock_services.login(request)


@router.get("/me")
def get_me(current_user: CurrentDashboardUserDep) -> AuthUserResponse:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: CurrentDashboardUserDep) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
