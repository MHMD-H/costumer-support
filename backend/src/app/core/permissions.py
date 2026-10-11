"""Tenant-scoped dashboard authorization and public-widget placeholder hooks."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.auth import CurrentDashboardUserDep
from app.core.rbac import Permission, Role, ROLE_GRANTABLE_PERMISSIONS, ROLE_PERMISSIONS
from app.core.tenant_context import (
    DashboardTenantDep,
    PublicWidgetTenantQueryDep,
    TenantContext,
    resolve_public_widget_tenant_from_body,
)
from app.db.postgres import DbSessionDep
from app.db.repositories import permissions as permission_repository
from app.features.schemas import PublicChatRequest


@dataclass(frozen=True)
class PublicWidgetChatContext:
    request: PublicChatRequest
    tenant: TenantContext


def forbidden(message: str = "Insufficient permission.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "forbidden", "message": message},
    )


def checked_role(value: Role | str) -> Role:
    try:
        return Role(value)
    except (TypeError, ValueError):
        raise forbidden("Dashboard role is invalid.") from None


def checked_permission(value: Permission | str) -> Permission:
    try:
        return Permission(value)
    except (TypeError, ValueError):
        raise forbidden("Dashboard permission is invalid.") from None


async def get_effective_permissions(
    current_user: CurrentDashboardUserDep,
    tenant: DashboardTenantDep,
    session: DbSessionDep,
) -> frozenset[Permission]:
    """Combine the trusted application role with allowed, same-tenant ACL rows."""
    role = checked_role(current_user.role)
    if current_user.tenant_id != tenant.tenant_id:
        raise forbidden()
    base = ROLE_PERMISSIONS[role]
    if role is not Role.TEAM_MEMBER:
        return base

    values = await permission_repository.list_user_permission_values(
        session, tenant.tenant_id, current_user.id
    )
    if any(assignment_tenant_id != tenant.tenant_id for _, assignment_tenant_id in values):
        raise forbidden("Stored permission belongs to another tenant.")
    grants = {checked_permission(value) for value, _ in values}
    if not grants <= ROLE_GRANTABLE_PERMISSIONS[role]:
        raise forbidden("Stored permission is not grantable to this role.")
    return base | grants


EffectivePermissionsDep = Annotated[
    frozenset[Permission], Depends(get_effective_permissions)
]


def require_roles(*allowed_roles: Role) -> Callable:
    if not allowed_roles or any(not isinstance(role, Role) for role in allowed_roles):
        raise TypeError("Role guards require closed Role values")

    def dependency(current_user: CurrentDashboardUserDep, tenant: DashboardTenantDep) -> None:
        if current_user.tenant_id != tenant.tenant_id or checked_role(current_user.role) not in allowed_roles:
            raise forbidden("Insufficient role.")

    return dependency


def require_permission(permission: Permission) -> Callable:
    if not isinstance(permission, Permission):
        raise TypeError("Permission guards require closed Permission values")

    async def dependency(effective: EffectivePermissionsDep) -> None:
        if permission not in effective:
            raise forbidden()

    return dependency


def require_conversation_access(effective: EffectivePermissionsDep) -> None:
    if not {
        Permission.VIEW_CONVERSATIONS,
        Permission.CREATE_CONVERSATIONS,
    } & effective:
        raise forbidden()


def require_shopify_connect(current_user: CurrentDashboardUserDep) -> None:
    """The sole permission guard that allows an authenticated unlinked merchant."""
    role = checked_role(current_user.role)
    if role is not Role.STORE_OWNER or Permission.CONNECT_SHOPIFY_STORE not in ROLE_PERMISSIONS[role]:
        raise forbidden()


def validate_allowed_origin(
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> None:
    """Placeholder allowed-origin validation hook for widget calls."""
    return None


def rate_limit_hook() -> None:
    """Placeholder rate limiting hook."""
    return None


def validate_public_widget_query(
    tenant: PublicWidgetTenantQueryDep,
    origin_ok: Annotated[None, Depends(validate_allowed_origin)] = None,
    rate_limit_ok: Annotated[None, Depends(rate_limit_hook)] = None,
) -> TenantContext:
    return tenant


def validate_public_widget_body(
    body: PublicChatRequest,
    origin_ok: Annotated[None, Depends(validate_allowed_origin)] = None,
    rate_limit_ok: Annotated[None, Depends(rate_limit_hook)] = None,
) -> PublicWidgetChatContext:
    return PublicWidgetChatContext(
        request=body,
        tenant=resolve_public_widget_tenant_from_body(body),
    )


PublicWidgetQueryDep = Annotated[TenantContext, Depends(validate_public_widget_query)]
PublicWidgetBodyDep = Annotated[
    PublicWidgetChatContext, Depends(validate_public_widget_body)
]
