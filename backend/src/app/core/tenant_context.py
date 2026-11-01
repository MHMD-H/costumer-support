"""Trusted dashboard and public-widget tenant contexts."""

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.db.postgres import DbSessionDep
from app.db.repositories import tenants as tenant_repository
from app.features.schemas import (
    PUBLIC_WIDGET_KEY_MAX_LENGTH,
    PUBLIC_WIDGET_SHOP_DOMAIN_MAX_LENGTH,
    PUBLIC_WIDGET_SHOP_ID_MAX_LENGTH,
    PublicChatRequest,
)
from app.features.shopify import normalize_shop_domain


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    shop_id: str | None = None
    shop_domain: str | None = None
    store_name: str | None = None
    widget_allowed_origins: tuple[str, ...] = ()
    widget_settings: dict[str, Any] | None = None


def resolve_dashboard_tenant(current_user: CurrentDashboardUserDep) -> TenantContext:
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Connect a Shopify store before accessing the dashboard."},
        )
    return TenantContext(tenant_id=current_user.tenant_id)


async def resolve_public_widget_tenant(
    session: DbSessionDep,
    *,
    shop_id: str | None,
    shop_domain: str | None,
    widget_public_key: str,
) -> TenantContext:
    normalized_shop_id = shop_id.strip() if shop_id else None
    normalized_shop_domain = normalize_shop_domain(shop_domain) if shop_domain else None
    normalized_widget_key = widget_public_key.strip()
    if not normalized_shop_id and not normalized_shop_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "bad_request",
                "message": "shop_id or shop_domain is required.",
            },
        )
    if not normalized_widget_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Widget public key is invalid."},
        )
    tenant = await tenant_repository.get_enabled_public_widget_tenant(
        session,
        shop_id=normalized_shop_id,
        shop_domain=normalized_shop_domain,
        widget_public_key=normalized_widget_key,
    )
    if tenant is None or not tenant.shop_domain:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Widget access is invalid."},
        )

    allowed_origins = tuple(
        value for value in tenant.widget_allowed_origins if isinstance(value, str)
    )
    settings = tenant.widget_settings if isinstance(tenant.widget_settings, dict) else {}
    return TenantContext(
        tenant_id=tenant.id,
        shop_id=tenant.shop_id,
        shop_domain=tenant.shop_domain,
        store_name=tenant.name,
        widget_allowed_origins=allowed_origins,
        widget_settings=settings,
    )


async def resolve_public_widget_tenant_from_query(
    session: DbSessionDep,
    shop_id: Annotated[str | None, Query(max_length=PUBLIC_WIDGET_SHOP_ID_MAX_LENGTH)] = None,
    shop_domain: Annotated[
        str | None, Query(max_length=PUBLIC_WIDGET_SHOP_DOMAIN_MAX_LENGTH)
    ] = None,
    widget_public_key: Annotated[
        str, Query(max_length=PUBLIC_WIDGET_KEY_MAX_LENGTH)
    ] = "",
) -> TenantContext:
    return await resolve_public_widget_tenant(
        session,
        shop_id=shop_id,
        shop_domain=shop_domain,
        widget_public_key=widget_public_key,
    )


async def resolve_public_widget_tenant_from_body(
    body: PublicChatRequest, session: DbSessionDep
) -> TenantContext:
    return await resolve_public_widget_tenant(
        session,
        shop_id=body.shop_id,
        shop_domain=body.shop_domain,
        widget_public_key=body.widget_public_key,
    )


CurrentTenant = TenantContext
CurrentTenantDep = Annotated[CurrentTenant, Depends(resolve_dashboard_tenant)]
# Keep existing route annotations compatible while making the trusted context
# explicit for new dependencies.
DashboardTenantDep = CurrentTenantDep
PublicWidgetTenantQueryDep = Annotated[
    TenantContext, Depends(resolve_public_widget_tenant_from_query)
]
PublicWidgetTenantBodyDep = Annotated[
    TenantContext, Depends(resolve_public_widget_tenant_from_body)
]
