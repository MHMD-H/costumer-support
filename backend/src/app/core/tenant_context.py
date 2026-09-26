"""Trusted dashboard and public-widget tenant contexts."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status

from app.core.auth import CurrentDashboardUserDep
from app.features.schemas import MOCK_TENANT_ID, PublicChatRequest


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    shop_id: str | None = None
    shop_domain: str | None = None
    widget_public_key: str | None = None


def resolve_dashboard_tenant(current_user: CurrentDashboardUserDep) -> TenantContext:
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Connect a Shopify store before accessing the dashboard."},
        )
    return TenantContext(tenant_id=current_user.tenant_id)


def resolve_public_widget_tenant(
    shop_id: str | None,
    shop_domain: str | None,
    widget_public_key: str,
) -> TenantContext:
    """Placeholder widget/store tenant resolver."""
    if not shop_id and not shop_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "bad_request",
                "message": "shop_id or shop_domain is required.",
            },
        )
    if not widget_public_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Widget public key is invalid."},
        )
    return TenantContext(
        tenant_id=MOCK_TENANT_ID,
        shop_id=shop_id,
        shop_domain=shop_domain or "example-store.myshopify.com",
        widget_public_key=widget_public_key,
    )


def resolve_public_widget_tenant_from_query(
    shop_id: Annotated[str | None, Query()] = None,
    shop_domain: Annotated[str | None, Query()] = None,
    widget_public_key: Annotated[str, Query()] = "",
) -> TenantContext:
    return resolve_public_widget_tenant(shop_id, shop_domain, widget_public_key)


def resolve_public_widget_tenant_from_body(body: PublicChatRequest) -> TenantContext:
    return resolve_public_widget_tenant(
        body.shop_id,
        body.shop_domain,
        body.widget_public_key,
    )


CurrentTenant = TenantContext
CurrentTenantDep = Annotated[CurrentTenant, Depends(resolve_dashboard_tenant)]
# Keep existing route annotations compatible while making the trusted context
# explicit for new dependencies.
DashboardTenantDep = CurrentTenantDep
PublicWidgetTenantQueryDep = Annotated[
    TenantContext, Depends(resolve_public_widget_tenant_from_query)
]
