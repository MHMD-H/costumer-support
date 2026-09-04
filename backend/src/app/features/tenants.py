"""Tenant use cases."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant
from app.db.repositories import tenants as tenant_repository
from app.features.schemas import TenantResponse, TenantUpdateRequest


def to_tenant_response(tenant: Tenant) -> TenantResponse:
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        shop_id=tenant.shop_id,
        shop_domain=tenant.shop_domain,
        widget_public_key=tenant.widget_public_key,
        widget_enabled=tenant.widget_enabled,
        widget_allowed_origins=tenant.widget_allowed_origins,
        widget_settings=tenant.widget_settings,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


async def get_tenant(session: AsyncSession, tenant_id: UUID, requested_tenant_id: UUID) -> TenantResponse:
    if tenant_id != requested_tenant_id:
        raise_not_found()

    tenant = await tenant_repository.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        raise_not_found()
    return to_tenant_response(tenant)


async def update_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    requested_tenant_id: UUID,
    request: TenantUpdateRequest,
) -> TenantResponse:
    if tenant_id != requested_tenant_id:
        raise_not_found()

    tenant = await tenant_repository.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        raise_not_found()

    updates = request.model_dump(exclude_unset=True)
    for non_nullable_field in ("name", "widget_enabled", "widget_allowed_origins", "widget_settings"):
        if updates.get(non_nullable_field) is None:
            updates.pop(non_nullable_field, None)
    await ensure_unique_updates(session, tenant, updates)
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        tenant = await tenant_repository.update_tenant(session, tenant, updates)
    return to_tenant_response(tenant)


async def ensure_unique_updates(session: AsyncSession, tenant: Tenant, updates: dict) -> None:
    if updates.get("shop_id") is not None and updates["shop_id"] != tenant.shop_id:
        existing = await tenant_repository.get_tenant_by_shop_id(session, updates["shop_id"])
        if existing is not None and existing.id != tenant.id:
            raise_conflict("A tenant with this shop ID already exists.")

    if updates.get("shop_domain") is not None and updates["shop_domain"] != tenant.shop_domain:
        existing = await tenant_repository.get_tenant_by_shop_domain(session, updates["shop_domain"])
        if existing is not None and existing.id != tenant.id:
            raise_conflict("A tenant with this shop domain already exists.")

    widget_public_key = updates.get("widget_public_key")
    if widget_public_key is not None and widget_public_key != tenant.widget_public_key:
        existing = await tenant_repository.get_tenant_by_widget_public_key(session, widget_public_key)
        if existing is not None and existing.id != tenant.id:
            raise_conflict("A tenant with this widget public key already exists.")


def raise_not_found() -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "message": "Tenant was not found."},
    )


def raise_conflict(message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "conflict", "message": message},
    )
