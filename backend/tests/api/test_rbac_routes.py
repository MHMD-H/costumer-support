"""Task 7 dashboard authorization at the HTTP boundary."""

from types import SimpleNamespace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_dashboard_user
from app.core.rbac import Role
from app.db.postgres import get_db_session
from app.db.repositories import permissions as permission_repository
from app.features import agent as agent_service
from app.features import documents as document_service
from app.features import mock_services
from app.features import permissions as permission_service
from app.features.conversations import service as conversation_service
from app.features.commerce import campaigns as campaign_service
from app.features.commerce import orders as order_service
from app.features.commerce import products as product_service
from app.features.commerce import sales as sales_service
from app.features.schemas import AuthUserResponse, PermissionListResponse
from app.features.users import service as user_service
from app.main import create_app


_DEFAULT_TENANT = object()


def client_for(monkeypatch, role: Role, *, grants=(), tenant_id=_DEFAULT_TENANT, user_id=None):
    tenant_id = uuid4() if tenant_id is _DEFAULT_TENANT else tenant_id
    user = AuthUserResponse(
        id=user_id or uuid4(), tenant_id=tenant_id, name="Dashboard User",
        email="user@example.com", role=role,
    )
    app = create_app()
    app.dependency_overrides[get_current_dashboard_user] = lambda: user

    async def no_database_session():
        yield None

    app.dependency_overrides[get_db_session] = no_database_session

    async def permission_values(_session, checked_tenant_id, checked_user_id):
        assert (checked_tenant_id, checked_user_id) == (tenant_id, user.id)
        return [(grant, tenant_id) for grant in grants]

    monkeypatch.setattr(permission_repository, "list_user_permission_values", permission_values)
    return TestClient(app), user


def stub_list_services(monkeypatch):
    async def products(_session, _tenant_id, **kwargs):
        return mock_services.list_products(kwargs["limit"], kwargs["offset"])

    async def orders(_session, _tenant_id, **kwargs):
        return mock_services.list_orders(kwargs["limit"], kwargs["offset"])

    async def campaigns(_session, _tenant_id, **kwargs):
        return mock_services.list_campaigns(kwargs["limit"], kwargs["offset"])

    async def documents(_session, _tenant_id, **kwargs):
        return mock_services.list_documents(kwargs["limit"], kwargs["offset"])

    async def users(_session, _tenant_id, **kwargs):
        return mock_services.list_users(kwargs["limit"], kwargs["offset"])

    async def sales(_session, _tenant_id, request):
        return mock_services.sales_summary(request)

    async def permissions(_session, _tenant_id, **kwargs):
        return PermissionListResponse(
            items=[], limit=kwargs["limit"], offset=kwargs["offset"],
            page=1, total=0, has_more=False,
        )

    monkeypatch.setattr(product_service, "list_products", products)
    monkeypatch.setattr(order_service, "list_orders", orders)
    monkeypatch.setattr(campaign_service, "list_campaigns", campaigns)
    monkeypatch.setattr(document_service, "list_documents", documents)
    monkeypatch.setattr(user_service, "list_users", users)
    monkeypatch.setattr(sales_service, "get_sales_summary", sales)
    monkeypatch.setattr(permission_service, "list_permissions", permissions)


@pytest.mark.parametrize(
    ("role", "grants", "method", "path", "body", "expected"),
    [
        (Role.STORE_OWNER, (), "GET", "/permissions", None, 200),
        (Role.ADMIN, (), "GET", "/users", None, 200),
        (Role.MARKETING_MANAGER, (), "GET", "/campaigns", None, 200),
        (Role.MARKETING_MANAGER, (), "GET", "/documents", None, 200),
        (Role.MARKETING_MANAGER, (), "POST", "/sales/summary", {}, 403),
        (Role.MARKETING_MANAGER, (), "GET", "/users", None, 403),
        (Role.TEAM_MEMBER, (), "GET", "/products", None, 200),
        (Role.TEAM_MEMBER, (), "GET", "/orders", None, 403),
        (Role.TEAM_MEMBER, ("view_orders",), "GET", "/orders", None, 200),
        (Role.TEAM_MEMBER, ("view_sales",), "POST", "/sales/summary", {}, 200),
        (Role.TEAM_MEMBER, ("view_campaigns",), "GET", "/campaigns", None, 403),
        (Role.TEAM_MEMBER, (), "GET", "/users", None, 403),
        (Role.TEAM_MEMBER, (), "GET", "/permissions", None, 403),
        (Role.TEAM_MEMBER, (), "GET", "/documents", None, 403),
    ],
)
def test_role_and_stored_grant_route_boundaries(
    monkeypatch, role, grants, method, path, body, expected
) -> None:
    stub_list_services(monkeypatch)
    client, _user = client_for(monkeypatch, role, grants=grants)

    response = client.request(method, path, json=body)

    assert response.status_code == expected, (role, grants, method, path, response.text)


def test_unlinked_owner_can_start_only_shopify_onboarding(monkeypatch) -> None:
    async def application_user(_session, user_id):
        return SimpleNamespace(id=user_id, tenant_id=None, role="store_owner")

    async def begin(_session, *, user, shop_domain):
        assert user.tenant_id is None
        return "https://example.myshopify.com/admin/oauth/authorize"

    monkeypatch.setattr("app.api.routes.shopify.user_repository.get_user_by_application_id", application_user)
    monkeypatch.setattr("app.api.routes.shopify.shopify_service.begin_connection", begin)
    client, _user = client_for(monkeypatch, Role.STORE_OWNER, tenant_id=None)
    response = client.get(
        "/shopify/connect?shop_domain=example.myshopify.com", follow_redirects=False
    )
    assert response.status_code == 307
    assert client.get("/products").status_code == 403

    other_client, _ = client_for(monkeypatch, Role.TEAM_MEMBER, tenant_id=None)
    assert other_client.get("/shopify/connect?shop_domain=example.myshopify.com").status_code == 403


def test_chat_and_search_filter_document_sources_and_underlying_data(monkeypatch) -> None:
    client, _user = client_for(monkeypatch, Role.TEAM_MEMBER)

    chat = client.post("/chat", json={"message": "Hi", "mode": "auto"})
    assert chat.status_code == 200
    assert chat.json()["sources"] == []
    assert chat.json()["message"]["sources"] == []
    assert chat.json()["used_tools"] == []
    assert client.post("/chat", json={"message": "Hi", "mode": "rag"}).status_code == 403
    assert client.post("/chat/stream", json={"message": "Hi", "mode": "rag"}).status_code == 403
    assert client.post("/search", json={"query": "policy", "scope": "knowledge"}).status_code == 403
    assert client.post("/search", json={"query": "orders", "scope": "orders"}).status_code == 403
    all_results = client.post("/search", json={"query": "data", "scope": "all"})
    assert all_results.status_code == 200
    assert [item["type"] for item in all_results.json()["items"]] == ["products"]

    granted_client, _ = client_for(monkeypatch, Role.TEAM_MEMBER, grants=("view_orders", "view_sales"))
    assert granted_client.post("/search", json={"query": "orders", "scope": "orders"}).status_code == 200
    agent_chat = granted_client.post("/chat", json={"message": "Sales", "mode": "agent"})
    assert agent_chat.status_code == 200
    assert agent_chat.json()["used_tools"] == ["get_sales"]
    assert agent_chat.json()["sources"] == []


def test_agent_tool_list_filters_before_pagination_by_data_permission(monkeypatch) -> None:
    seen = []

    async def tools(_session, _tenant_id, *, limit, offset, allowed_names):
        seen.append(allowed_names)
        rows = [
            SimpleNamespace(
                name=name, description=name, input_schema={}, read_only=True
            )
            for name in sorted(allowed_names)
        ]
        return rows[offset:offset + limit], len(rows)

    monkeypatch.setattr(agent_service.agent_tool_repository, "list_agent_tools", tools)
    client, _ = client_for(monkeypatch, Role.TEAM_MEMBER)
    response = client.get("/agent/tools")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["get_products"]
    assert seen[-1] == frozenset({"get_products"})

    granted_client, _ = client_for(monkeypatch, Role.TEAM_MEMBER, grants=("view_orders", "view_sales"))
    response = granted_client.get("/agent/tools")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == [
        "get_orders", "get_products", "get_sales"
    ]


def test_team_member_conversation_grant_limits_access_to_owned_conversations(monkeypatch) -> None:
    tenant_id, user_id, other_user_id = uuid4(), uuid4(), uuid4()
    own_id, other_id = uuid4(), uuid4()
    now = datetime.now(timezone.utc)

    async def get_conversation(_session, checked_tenant_id, conversation_id):
        assert checked_tenant_id == tenant_id
        return SimpleNamespace(
            id=conversation_id, tenant_id=tenant_id,
            user_id=user_id if conversation_id == own_id else other_user_id,
            surface="dashboard", title="Conversation", status="active",
            created_at=now, updated_at=now,
        )

    async def create_conversation(_session, checked_tenant_id, checked_user_id, _request):
        assert (checked_tenant_id, checked_user_id) == (tenant_id, user_id)
        return mock_services.conversation_response(own_id)

    monkeypatch.setattr(conversation_service.conversation_repository, "get_conversation_by_id", get_conversation)
    monkeypatch.setattr(conversation_service, "create_conversation", create_conversation)
    denied_client, _ = client_for(
        monkeypatch, Role.TEAM_MEMBER, tenant_id=tenant_id, user_id=user_id
    )
    assert denied_client.post("/conversations", json={}).status_code == 403
    assert denied_client.get(f"/conversations/{own_id}").status_code == 403

    client, _ = client_for(
        monkeypatch, Role.TEAM_MEMBER, grants=("create_conversations",),
        tenant_id=tenant_id, user_id=user_id,
    )
    assert client.post("/conversations", json={}).status_code == 201
    assert client.get(f"/conversations/{own_id}").status_code == 200
    assert client.get(f"/conversations/{other_id}").status_code == 404
    assert client.patch(f"/conversations/{other_id}", json={"title": "Changed"}).status_code == 404


def test_team_member_cannot_read_document_sourced_messages_without_view_documents(monkeypatch) -> None:
    tenant_id, user_id, conversation_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)

    async def get_conversation(*_args):
        return SimpleNamespace(
            id=conversation_id, tenant_id=tenant_id, user_id=user_id,
            surface="dashboard", title="Conversation", status="active",
            created_at=now, updated_at=now,
        )

    async def list_messages(*_args, **_kwargs):
        return [SimpleNamespace(sources=[{"document_id": str(uuid4())}])]

    monkeypatch.setattr(conversation_service.conversation_repository, "get_conversation_by_id", get_conversation)
    monkeypatch.setattr(conversation_service.conversation_repository, "list_messages", list_messages)
    client, _ = client_for(
        monkeypatch, Role.TEAM_MEMBER, grants=("create_conversations",),
        tenant_id=tenant_id, user_id=user_id,
    )
    assert client.get(f"/conversations/{conversation_id}/messages").status_code == 403


def test_unknown_permission_request_returns_403_after_authentication(monkeypatch) -> None:
    client, _ = client_for(monkeypatch, Role.STORE_OWNER)
    response = client.patch(
        f"/permissions/{uuid4()}", json={"permission": "super_permission"}
    )
    assert response.status_code == 403
    assert TestClient(create_app()).patch(
        f"/permissions/{uuid4()}", json={"permission": "super_permission"}
    ).status_code == 401
