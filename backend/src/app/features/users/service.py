"""User management use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import users as user_repository
from app.features.pagination import page
from app.features.schemas import DashboardRole, UserListResponse, UserResponse


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def list_users(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int,
    offset: int,
) -> UserListResponse:
    users, total = await user_repository.list_users(session, tenant_id, limit, offset)
    return UserListResponse(
        items=[to_user_response(user) for user in users],
        page=page(limit, offset, total),
    )


async def get_user(session: AsyncSession, tenant_id: UUID, user_id: UUID) -> UserResponse:
    user = await user_repository.get_user_by_id(session, tenant_id, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "User was not found."},
        )
    return to_user_response(user)


async def create_user(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    auth_user_id: UUID,
    name: str,
    email: str,
    role: DashboardRole,
) -> UserResponse:
    existing_auth_user = await user_repository.get_user_by_auth_user_id(session, auth_user_id)
    if existing_auth_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "A user with this auth user ID already exists."},
        )

    existing_email = await user_repository.get_user_by_email(session, tenant_id, email)
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "conflict", "message": "A user with this email already exists for the tenant."},
        )

    user = await user_repository.create_user(
        session,
        tenant_id=tenant_id,
        auth_user_id=auth_user_id,
        name=name,
        email=email,
        role=role,
    )
    return to_user_response(user)
