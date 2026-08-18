"""Tests for commerce API routes."""

from fastapi.testclient import TestClient

from app.main import create_app


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


def test_protected_commerce_routes_return_mock_data_with_auth() -> None:
    client = TestClient(create_app())
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
