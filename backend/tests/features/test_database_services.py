"""Tests for database-backed service behavior without a live database."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.db.models import Product
from app.features.commerce import products as product_service


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
PRODUCT_ID = UUID("77777777-7777-7777-7777-777777777777")


def test_product_service_returns_404_when_product_is_missing(monkeypatch) -> None:
    async def missing_product(session, tenant_id, product_id):
        return None

    monkeypatch.setattr(product_service.product_repository, "get_product_by_id", missing_product)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(product_service.get_product(None, TENANT_ID, PRODUCT_ID))

    assert exc.value.status_code == 404
    assert exc.value.detail["message"] == "Product was not found."


def test_product_service_maps_list_response(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    product = Product(
        id=PRODUCT_ID,
        tenant_id=TENANT_ID,
        external_product_id="shopify-product-1",
        name="Database Product",
        description="Stored product.",
        category="Demo",
        price=Decimal("19.99"),
        status="active",
        public_visible=True,
        created_at=now,
        updated_at=now,
    )

    async def list_products(session, tenant_id, *, status, category, limit, offset):
        return [product], 1

    monkeypatch.setattr(product_service.product_repository, "list_products", list_products)

    response = asyncio.run(
        product_service.list_products(
            None,
            TENANT_ID,
            status="active",
            category=None,
            limit=20,
            offset=0,
        )
    )

    assert response.items[0].name == "Database Product"
    assert response.items[0].tenant_id == TENANT_ID
    assert response.page.total == 1
