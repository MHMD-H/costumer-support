"""Tests for database-backed service behavior without a live database."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.db.models import Product
from app.db.models import Campaign, Document
from app.features.commerce import campaigns as campaign_service
from app.features import documents as document_service
from app.features.commerce import products as product_service
from app.features.schemas import CampaignCreateRequest, DocumentUpdateRequest


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
PRODUCT_ID = UUID("77777777-7777-7777-7777-777777777777")
CAMPAIGN_ID = UUID("88888888-8888-8888-8888-888888888888")
DOCUMENT_ID = UUID("99999999-9999-9999-9999-999999999999")


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
    assert response.total == 1
    assert response.page == 1
    assert response.has_more is False


def test_campaign_create_conflict_raises_409(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    campaign = Campaign(
        id=CAMPAIGN_ID,
        tenant_id=TENANT_ID,
        name="Holiday",
        channel="email",
        spend=Decimal("10.00"),
        revenue=Decimal("20.00"),
        roas=Decimal("2.0000"),
        created_at=now,
        updated_at=now,
    )

    async def existing_campaign(session, tenant_id, name, channel):
        return campaign

    monkeypatch.setattr(
        campaign_service.campaign_repository,
        "get_campaign_by_name_and_channel",
        existing_campaign,
    )

    request = CampaignCreateRequest(
        name="Holiday",
        channel="email",
        spend=Decimal("10.00"),
        revenue=Decimal("20.00"),
        roas=Decimal("2.0000"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(campaign_service.create_campaign(None, TENANT_ID, request))

    assert exc.value.status_code == 409


def test_document_patch_maps_metadata_field(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    document = Document(
        id=DOCUMENT_ID,
        tenant_id=TENANT_ID,
        uploaded_by_user_id=UUID("22222222-2222-2222-2222-222222222222"),
        title="Old",
        type="txt",
        source="old.txt",
        visibility="internal",
        status="uploaded",
        metadata_={},
        created_at=now,
        updated_at=now,
    )
    captured_updates = {}

    async def get_document_by_id(session, tenant_id, document_id):
        return document

    async def update_document(session, document, updates):
        captured_updates.update(updates)
        for field, value in updates.items():
            setattr(document, field, value)
        return document

    async def count_document_chunks(session, tenant_id, document_id):
        return 0

    monkeypatch.setattr(document_service.document_repository, "get_document_by_id", get_document_by_id)
    monkeypatch.setattr(document_service.document_repository, "update_document", update_document)
    monkeypatch.setattr(document_service.document_repository, "count_document_chunks", count_document_chunks)

    response = asyncio.run(
        document_service.update_document(
            None,
            TENANT_ID,
            DOCUMENT_ID,
            DocumentUpdateRequest(metadata={"source": "manual"}, title="New"),
        )
    )

    assert response.title == "New"
    assert captured_updates["metadata_"] == {"source": "manual"}
    assert "metadata" not in captured_updates


def test_document_replacement_builds_chunks() -> None:
    now = datetime.now(timezone.utc)
    document = Document(
        id=DOCUMENT_ID,
        tenant_id=TENANT_ID,
        uploaded_by_user_id=UUID("22222222-2222-2222-2222-222222222222"),
        title="Policy",
        type="txt",
        source="policy.txt",
        visibility="public",
        status="processing",
        metadata_={},
        created_at=now,
        updated_at=now,
    )

    chunks = document_service.build_replacement_chunks(document, "hello")

    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["content"] == "hello"
    assert chunks[0]["metadata"]["tenant_id"] == str(TENANT_ID)
