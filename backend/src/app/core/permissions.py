"""RBAC, ACL, and public-widget permission checks.

Public security current status: placeholder widget/origin/rate-limit validation.
Why placeholder: local/mock widget tests need the public API contract before
production store validation exists.
Replace when: public widget is exposed beyond local/mock testing.
Target implementation: widget key validation, allowed-origin checks, tenant
lookup, and rate limiting.

Dashboard permissions current status: simple role checks with placeholder ACL
behavior. Replace with DB-backed permissions when user, tenant, and permission
records are implemented.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.auth import CurrentDashboardUserDep
from app.core.tenant_context import (
    PublicWidgetTenantQueryDep,
    TenantContext,
    resolve_public_widget_tenant_from_body,
)
from app.features.schemas import DashboardRole, PublicChatRequest


@dataclass(frozen=True)
class PublicWidgetChatContext:
    request: PublicChatRequest
    tenant: TenantContext


def require_roles(*allowed_roles: DashboardRole) -> Callable[[CurrentDashboardUserDep], None]:
    def dependency(current_user: CurrentDashboardUserDep) -> None:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "forbidden", "message": "Insufficient role."},
            )

    return dependency


def require_permission(permission: str) -> Callable[[CurrentDashboardUserDep], None]:
    def dependency(current_user: CurrentDashboardUserDep) -> None:
        if current_user.role in {"store_owner", "admin"}:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "message": f"Permission '{permission}' is required.",
            },
        )

    return dependency


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
