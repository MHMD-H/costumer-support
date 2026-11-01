"""Tenant-scoped dashboard authorization and public-widget access checks."""

from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from os import getenv
from threading import Lock
from time import monotonic
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.auth import CurrentApplicationUserDep, CurrentDashboardUserDep
from app.core.rbac import Permission, Role, ROLE_GRANTABLE_PERMISSIONS, ROLE_PERMISSIONS
from app.core.tenant_context import (
    DashboardTenantDep,
    PublicWidgetTenantBodyDep,
    PublicWidgetTenantQueryDep,
    TenantContext,
)
from app.db.postgres import DbSessionDep
from app.db.repositories import permissions as permission_repository
from app.features.schemas import PublicChatRequest


@dataclass(frozen=True)
class PublicWidgetChatContext:
    request: PublicChatRequest
    tenant: TenantContext


class PublicWidgetRateLimiter:
    """Bounded sliding-window limiter for the current single-process deployment."""

    def __init__(self, *, request_limit: int, window_seconds: float, max_clients: int = 10_000) -> None:
        if request_limit < 1 or window_seconds <= 0 or max_clients < 1:
            raise ValueError("Public widget rate-limit settings must be positive")
        self.request_limit = request_limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._requests: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(self, client_key: str, *, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            timestamps = self._requests.pop(client_key, deque())
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.request_limit:
                self._requests[client_key] = timestamps
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limited",
                        "message": "Please wait before sending another request.",
                    },
                )
            timestamps.append(current)
            self._requests[client_key] = timestamps
            while len(self._requests) > self.max_clients:
                self._requests.popitem(last=False)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


def _positive_number(name: str, default: str, cast: Callable[[str], int | float]) -> int | float:
    value = cast(getenv(name, default))
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


PUBLIC_WIDGET_RATE_LIMITER = PublicWidgetRateLimiter(
    request_limit=int(_positive_number("PUBLIC_WIDGET_RATE_LIMIT_REQUESTS", "60", int)),
    window_seconds=float(
        _positive_number("PUBLIC_WIDGET_RATE_LIMIT_WINDOW_SECONDS", "60", float)
    ),
)


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


def require_shopify_connect(current_user: CurrentApplicationUserDep) -> None:
    """The sole permission guard that allows an authenticated unlinked merchant."""
    role = checked_role(current_user.role)
    if role is not Role.STORE_OWNER or Permission.CONNECT_SHOPIFY_STORE not in ROLE_PERMISSIONS[role]:
        raise forbidden()


def normalized_https_origin(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        return None
    hostname = parsed.hostname.lower()
    return f"https://{hostname}" + (f":{port}" if port not in {None, 443} else "")


def validate_allowed_origin(origin: str | None, tenant: TenantContext) -> None:
    normalized_origin = normalized_https_origin(origin) if origin else None
    allowed = {
        normalized
        for value in tenant.widget_allowed_origins
        if (normalized := normalized_https_origin(value)) is not None
    }
    if normalized_origin is None or normalized_origin not in allowed:
        raise forbidden("Storefront origin is not allowed.")


def rate_limit_hook(request: Request) -> None:
    client_host = request.client.host if request.client is not None else "unknown"
    PUBLIC_WIDGET_RATE_LIMITER.check(client_host)


PublicWidgetRateLimitDep = Annotated[None, Depends(rate_limit_hook)]


def validate_public_widget_query(
    rate_limit_ok: PublicWidgetRateLimitDep,
    tenant: PublicWidgetTenantQueryDep,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> TenantContext:
    validate_allowed_origin(origin, tenant)
    return tenant


def validate_public_widget_body(
    body: PublicChatRequest,
    rate_limit_ok: PublicWidgetRateLimitDep,
    tenant: PublicWidgetTenantBodyDep,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> PublicWidgetChatContext:
    validate_allowed_origin(origin, tenant)
    return PublicWidgetChatContext(
        request=body,
        tenant=tenant,
    )


PublicWidgetQueryDep = Annotated[TenantContext, Depends(validate_public_widget_query)]
PublicWidgetBodyDep = Annotated[
    PublicWidgetChatContext, Depends(validate_public_widget_body)
]
