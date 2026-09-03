"""Tests for commerce API routes."""

from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db_session
from app.features import mock_services
from app.features.commerce import campaigns as campaign_service
from app.features.commerce import orders as order_service
from app.features.commerce import products as product_service
from app.features.commerce import sales as sales_service
from app.main import create_app


async def fake_db_session() -> AsyncGenerator[AsyncSession, None]:
    yield None


def test_protected_commerce_routes_require_auth() -> None:
    client = TestClient(create_app())

    for method, path, json_body in [
        ("GET", "/products", None),
        ("GET", "/orders", None),
        ("POST", "/sales/summary", {}),
        ("GET", "/campaigns", None),
    ]:
        response = client.request(method, path, json=json_body)
        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"


def test_protected_commerce_routes_call_services_with_auth(monkeypatch) -> None:
    async def fake_list_products(session, tenant_id, *, status, category, limit, offset):
        return mock_services.list_products(limit, offset)

    async def fake_list_orders(session, tenant_id, *, status, user_id, limit, offset):
        return mock_services.list_orders(limit, offset)

    async def fake_sales_summary(session, tenant_id, request):
        return mock_services.sales_summary(request)

    async def fake_list_campaigns(session, tenant_id, *, channel, limit, offset):
        return mock_services.list_campaigns(limit, offset)

    monkeypatch.setattr(product_service, "list_products", fake_list_products)
    monkeypatch.setattr(order_service, "list_orders", fake_list_orders)
    monkeypatch.setattr(sales_service, "get_sales_summary", fake_sales_summary)
    monkeypatch.setattr(campaign_service, "list_campaigns", fake_list_campaigns)

    app = create_app()
    app.dependency_overrides[get_db_session] = fake_db_session
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    products = client.get("/products", headers=headers)
    orders = client.get("/orders", headers=headers)
    sales = client.post("/sales/summary", headers=headers, json={})
    campaigns = client.get("/campaigns", headers=headers)

    assert products.status_code == 200
    assert products.json()["items"][0]["name"] == "Mock Product"
    assert orders.status_code == 200
    assert orders.json()["items"][0]["status"] == "paid"
    assert sales.status_code == 200
    assert sales.json()["order_count"] == 10
    assert campaigns.status_code == 200
    assert campaigns.json()["items"][0]["channel"] == "email"
