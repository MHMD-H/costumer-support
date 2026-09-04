"""Permission use cases."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Permission
from app.db.repositories import permissions as permission_repository
from app.features.pagination import page
from app.features.schemas import PermissionListResponse, PermissionResponse, PermissionUpdateRequest


def to_permission_response(permission: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=permission.id,
        tenant_id=permission.tenant_id,
        user_id=permission.user_id,
        permission=permission.permission,
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
    return PermissionListResponse(
        items=[to_permission_response(permission) for permission in permissions],
        page=page(limit, offset, total),
    )


async def update_permission(
    session: AsyncSession,
    tenant_id: UUID,
    permission_id: UUID,
    request: PermissionUpdateRequest,
) -> PermissionResponse:
    permission = await permission_repository.get_permission_by_id(session, tenant_id, permission_id)
    if permission is None:
        raise_not_found()

    updates = {
        field: value
        for field, value in request.model_dump(exclude_unset=True).items()
        if value is not None
    }
    new_value = updates.get("permission")
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
