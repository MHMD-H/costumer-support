from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, CurrentUserDep, get_current_dashboard_user
from app.core.tenant_context import (
    CurrentTenant,
    CurrentTenantDep,
    DashboardTenantDep,
    TenantContext,
)
from app.db.postgres import get_db_session
from app.features import mock_services
from app.features.schemas import AuthUserResponse, ProductListResponse
from app.main import create_app


def test_current_context_aliases_preserve_trusted_dependency_types() -> None:
    assert CurrentUser is AuthUserResponse
    assert CurrentUserDep.__metadata__[0].dependency is get_current_dashboard_user
    assert CurrentTenant is TenantContext
    assert DashboardTenantDep is CurrentTenantDep


def test_request_tenant_inputs_cannot_override_current_tenant(monkeypatch) -> None:
    trusted_tenant_id = uuid4()
    attacker_tenant_id = uuid4()
    current_user = mock_services.mock_auth_user().model_copy(
        update={"tenant_id": trusted_tenant_id}
    )
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = lambda: current_user

    async def no_database_session():
        yield None

    app.dependency_overrides[get_db_session] = no_database_session
    received_tenant_ids = []

    async def list_products(_session, tenant_id, **_kwargs):
        received_tenant_ids.append(tenant_id)
        return ProductListResponse(
            items=[], limit=20, offset=0, page=1, total=0, has_more=False
        )

    monkeypatch.setattr("app.api.routes.products.product_service.list_products", list_products)
    client = TestClient(app)

    response = client.get(
        "/products",
        params={"tenant_id": str(attacker_tenant_id)},
        headers={"X-Tenant-ID": str(attacker_tenant_id)},
    )

    assert response.status_code == 200
    assert received_tenant_ids == [trusted_tenant_id]


def test_body_and_path_tenant_inputs_do_not_override_current_tenant(monkeypatch) -> None:
    trusted_tenant_id = uuid4()
    attacker_tenant_id = uuid4()
    current_user = mock_services.mock_auth_user().model_copy(
        update={"tenant_id": trusted_tenant_id}
    )
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = lambda: current_user

    async def no_database_session():
        yield None

    app.dependency_overrides[get_db_session] = no_database_session
    captured = {}

    async def update_tenant(_session, tenant_id, requested_tenant_id, request):
        captured.update(
            tenant_id=tenant_id,
            requested_tenant_id=requested_tenant_id,
            request_tenant_id=getattr(request, "tenant_id", None),
        )
        raise HTTPException(status_code=418)

    monkeypatch.setattr("app.features.tenants.update_tenant", update_tenant)
    client = TestClient(app)

    response = client.patch(
        f"/tenants/{trusted_tenant_id}",
        json={"tenant_id": str(attacker_tenant_id), "name": "ignored"},
    )
    mismatched_path = client.get(f"/tenants/{attacker_tenant_id}")

    assert response.status_code == 418
    assert captured == {
        "tenant_id": trusted_tenant_id,
        "requested_tenant_id": trusted_tenant_id,
        "request_tenant_id": None,
    }
    assert mismatched_path.status_code == 404
