"""Permission use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Permission
from app.db.repositories import permissions as permission_repository
from app.db.repositories import users as user_repository
from app.core.permissions import checked_permission, checked_role, forbidden
from app.core.rbac import Permission as PermissionValue, Role, ROLE_GRANTABLE_PERMISSIONS, ROLE_PERMISSIONS
from app.features.pagination import offset_pagination
from app.features.schemas import AuthUserResponse, PermissionListResponse, PermissionResponse, PermissionUpdateRequest


def to_permission_response(permission: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=permission.id,
        tenant_id=permission.tenant_id,
        user_id=permission.user_id,
        permission=checked_permission(permission.permission),
        created_at=permission.created_at,
    )


async def list_permissions(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    user_id: UUID | None,
    limit: int,
    offset: int,
) -> PermissionListResponse:
    permissions, total = await permission_repository.list_permissions(
        session,
        tenant_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return offset_pagination(
        PermissionListResponse,
        [to_permission_response(permission) for permission in permissions],
        limit=limit,
        offset=offset,
        total=total,
    )


async def update_permission(
    session: AsyncSession,
    tenant_id: UUID,
    permission_id: UUID,
    request: PermissionUpdateRequest,
    *,
    acting_user: AuthUserResponse | None = None,
) -> PermissionResponse:
    permission = await permission_repository.get_permission_by_id(session, tenant_id, permission_id)
    if permission is None:
        raise_not_found()

    if acting_user is None or acting_user.tenant_id != tenant_id:
        raise forbidden()
    actor_role = checked_role(acting_user.role)
    actor_permissions = ROLE_PERMISSIONS[actor_role]
    if actor_role not in {Role.STORE_OWNER, Role.ADMIN} or PermissionValue.MANAGE_PERMISSIONS not in actor_permissions:
        raise forbidden()
    if permission.user_id == acting_user.id:
        raise forbidden("Users cannot grant themselves permissions.")
    target_user = await user_repository.get_user_by_id(session, tenant_id, permission.user_id)
    if target_user is None or target_user.tenant_id != tenant_id:
        raise forbidden("Permission target is outside the current tenant.")
    target_role = checked_role(target_user.role)
    grantable = ROLE_GRANTABLE_PERMISSIONS.get(target_role, frozenset())
    if checked_permission(permission.permission) not in grantable:
        raise forbidden("Stored permission is not grantable to this role.")

    updates = {
        field: checked_permission(value).value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    new_value = updates.get("permission")
    if new_value is not None and (
        checked_permission(new_value) not in grantable
        or checked_permission(new_value) not in actor_permissions
    ):
        raise forbidden("Permission cannot be granted to this user.")
    if new_value is not None and new_value != permission.permission:
        existing = await permission_repository.get_permission_by_value(
            session,
            tenant_id,
            permission.user_id,
            new_value,
        )
        if existing is not None and existing.id != permission.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "conflict", "message": "This permission already exists for the user."},
            )

    if updates:
        permission = await permission_repository.update_permission(session, permission, updates)
    return to_permission_response(permission)


def raise_not_found() -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "message": "Permission was not found."},
    )
