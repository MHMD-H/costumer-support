"""User management use cases."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import users as user_repository
from app.core.permissions import checked_role, forbidden
from app.core.rbac import Permission, ROLE_PERMISSIONS
from app.features.pagination import offset_pagination
from app.features.schemas import AuthUserResponse, DashboardRole, UserListResponse, UserResponse, UserUpdateRequest


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        name=user.name,
        email=user.email,
        role=checked_role(user.role),
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
    return offset_pagination(
        UserListResponse,
        [to_user_response(user) for user in users],
        limit=limit,
        offset=offset,
        total=total,
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
        role=checked_role(role).value,
    )
    return to_user_response(user)


async def update_user(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    request: UserUpdateRequest,
    *,
    acting_user: AuthUserResponse | None = None,
) -> UserResponse:
    user = await user_repository.get_user_by_id(session, tenant_id, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "User was not found."},
        )

    updates = {
        field: value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if "role" in updates:
        if acting_user is None or acting_user.tenant_id != tenant_id:
            raise forbidden()
        if acting_user.id == user.id:
            raise forbidden("Users cannot change their own role.")
        actor_permissions = ROLE_PERMISSIONS[checked_role(acting_user.role)]
        if Permission.MANAGE_USERS not in actor_permissions:
            raise forbidden()
        if not ROLE_PERMISSIONS[checked_role(user.role)] <= actor_permissions:
            raise forbidden("Cannot manage a more privileged user.")
        if not ROLE_PERMISSIONS[checked_role(updates["role"])] <= actor_permissions:
            raise forbidden("Cannot assign a more privileged role.")
        updates["role"] = checked_role(updates["role"]).value
    email = updates.get("email")
    if email is not None and email != user.email:
        existing = await user_repository.get_user_by_email(session, tenant_id, email)
        if existing is not None and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "conflict", "message": "A user with this email already exists for the tenant."},
            )

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        user = await user_repository.update_user(session, user, updates)
    return to_user_response(user)
