"""Tests for PostgreSQL repository query construction."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.db.models import Product
from app.db.repositories import conversations, products


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
