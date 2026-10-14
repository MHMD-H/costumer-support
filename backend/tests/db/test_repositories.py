"""Tests for PostgreSQL repository query construction."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.db.models import Product
from app.db.repositories import agent_tools, conversations, permissions, products, shopify, users


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
PRODUCT_ID = UUID("22222222-2222-2222-2222-222222222222")
CONVERSATION_ID = UUID("33333333-3333-3333-3333-333333333333")
CURSOR_ID = UUID("44444444-4444-4444-4444-444444444444")


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value


class CapturingSession:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


def sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_product_list_applies_tenant_filter_offset_and_stable_ordering() -> None:
    now = datetime.now(timezone.utc)
    product = Product(
        id=PRODUCT_ID,
        tenant_id=TENANT_ID,
        name="Product",
        status="active",
        created_at=now,
        updated_at=now,
    )
    session = CapturingSession([ScalarResult(3), ScalarResult([product])])

    rows, total = asyncio.run(
        products.list_products(
            session,
            TENANT_ID,
            status="active",
            category=None,
            limit=20,
            offset=40,
        )
    )

    statement_sql = sql(session.statements[1])
    assert rows == [product]
    assert total == 3
    assert "products.tenant_id" in statement_sql
    assert "products.status" in statement_sql
    assert "ORDER BY products.created_at DESC, products.id DESC" in statement_sql
    assert "LIMIT 20 OFFSET 40" in statement_sql


def test_conversation_cursor_list_uses_created_at_and_id_boundary() -> None:
    cursor_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session = CapturingSession([ScalarResult([])])

    asyncio.run(
        conversations.list_conversations(
            session,
            TENANT_ID,
            status="active",
            limit=20,
            cursor_created_at=cursor_time,
            cursor_id=CURSOR_ID,
        )
    )

    statement_sql = sql(session.statements[0])
    assert "(conversations.created_at, conversations.id) <" in statement_sql
    assert "ORDER BY conversations.created_at DESC, conversations.id DESC" in statement_sql
    assert "LIMIT 21" in statement_sql
    assert str(TENANT_ID) in statement_sql
    assert "'dashboard'" in statement_sql


def test_acl_values_require_matching_permission_and_user_tenants() -> None:
    user_id = UUID("55555555-5555-5555-5555-555555555555")
    session = CapturingSession([ScalarResult([("view_orders", TENANT_ID)])])

    values = asyncio.run(
        permissions.list_user_permission_values(session, TENANT_ID, user_id)
    )

    statement_sql = sql(session.statements[0])
    assert values == [("view_orders", TENANT_ID)]
    assert "permissions.tenant_id" in statement_sql
    assert f"permissions.tenant_id = '{TENANT_ID}'" not in statement_sql
    assert f"permissions.user_id = '{user_id}'" in statement_sql
    assert f"users.tenant_id = '{TENANT_ID}'" in statement_sql


def test_agent_tool_list_filters_names_before_database_pagination() -> None:
    session = CapturingSession([ScalarResult(0), ScalarResult([])])

    asyncio.run(agent_tools.list_agent_tools(
        session, TENANT_ID, limit=20, offset=0,
        allowed_names=frozenset({"get_products"}),
    ))

    assert all("agent_tools.name IN ('get_products')" in sql(statement) for statement in session.statements)
    assert all("agent_tools.read_only IS true" in sql(statement) for statement in session.statements)


def test_new_merchant_insert_is_idempotent_and_unlinked(monkeypatch) -> None:
    auth_user_id = UUID("66666666-6666-6666-6666-666666666666")
    existing_user = object()

    class Session(CapturingSession):
        async def commit(self):
            pass

    async def get_existing(_session, received_id):
        assert received_id == auth_user_id
        return existing_user

    monkeypatch.setattr(users, "get_user_by_auth_user_id", get_existing)
    session = Session([None])
    result = asyncio.run(users.create_unlinked_store_owner(
        session, auth_user_id=auth_user_id, email="merchant@example.com"
    ))

    statement_sql = sql(session.statements[0])
    assert result is existing_user
    assert "ON CONFLICT ON CONSTRAINT users_auth_user_id_key DO NOTHING" in statement_sql
    assert "NULL" in statement_sql
    assert "'store_owner'" in statement_sql
    assert "'merchant@example.com'" in statement_sql
    assert str(auth_user_id) in statement_sql


def test_shopify_callback_user_lookup_locks_current_role() -> None:
    user_id = UUID("77777777-7777-7777-7777-777777777777")

    class Result:
        def scalar_one_or_none(self):
            return None

    session = CapturingSession([Result()])
    asyncio.run(shopify.get_user(session, user_id))

    statement_sql = sql(session.statements[0])
    assert f"users.id = '{user_id}'" in statement_sql
    assert "FOR UPDATE OF users" in statement_sql
