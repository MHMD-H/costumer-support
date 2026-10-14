"""Tenant predicates for dashboard resource repository reads."""

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.features import agent, documents as document_service, permissions as permission_service
from app.features.commerce import campaigns as campaign_service
from app.features.commerce import orders as order_service, products as product_service
from app.features.conversations import service as conversation_service
from app.features.feedback import service as feedback_service
from app.features.schemas import (
    AgentToolUpdateRequest,
    CampaignUpdateRequest,
    ConversationUpdateRequest,
    DocumentUpdateRequest,
    FeedbackUpdateRequest,
    PermissionUpdateRequest,
    UserUpdateRequest,
)
from app.features.users import service as user_service
from app.db.repositories import (
    agent_tools,
    campaigns,
    conversations,
    documents,
    feedback,
    orders,
    permissions,
    products,
    sales,
    users,
)


TENANT_ID = uuid4()
RESOURCE_ID = uuid4()


class Result:
    def scalar_one(self):
        return 0

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []

    def one(self):
        return 0, 0


class CapturingSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return Result()


def compile_sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_tenant_owned_repository_reads_include_the_trusted_tenant_predicate() -> None:
    async def run_checks() -> None:
        checks = [
            ("products.get", "products", lambda s: products.get_product_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("products.list", "products", lambda s: products.list_products(s, TENANT_ID, status=None, category=None, limit=10, offset=0)),
            ("orders.get", "orders", lambda s: orders.get_order_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("orders.list", "orders", lambda s: orders.list_orders(s, TENANT_ID, status=None, user_id=None, limit=10, offset=0)),
            ("sales.summary", "sales", lambda s: sales.get_sales_summary(s, TENANT_ID, start_date=None, end_date=None, product_id=None)),
            ("campaigns.get", "campaigns", lambda s: campaigns.get_campaign_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("campaigns.duplicate-check", "campaigns", lambda s: campaigns.get_campaign_by_name_and_channel(s, TENANT_ID, "name", "email")),
            ("campaigns.list", "campaigns", lambda s: campaigns.list_campaigns(s, TENANT_ID, channel=None, limit=10, offset=0)),
            ("documents.get", "documents", lambda s: documents.get_document_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("documents.list", "documents", lambda s: documents.list_documents(s, TENANT_ID, document_type=None, status=None, visibility=None, limit=10, offset=0)),
            ("documents.chunk-count", "document_chunks", lambda s: documents.count_document_chunks(s, TENANT_ID, RESOURCE_ID)),
            ("documents.chunks", "document_chunks", lambda s: documents.list_document_chunks(s, TENANT_ID, RESOURCE_ID, limit=10, offset=0)),
            ("conversations.get", "conversations", lambda s: conversations.get_conversation_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("conversations.list", "conversations", lambda s: conversations.list_conversations(s, TENANT_ID, status=None, limit=10, cursor_created_at=None, cursor_id=None)),
            ("messages.get", "messages", lambda s: conversations.get_message_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("messages.list", "messages", lambda s: conversations.list_messages(s, TENANT_ID, RESOURCE_ID, limit=10, cursor_created_at=None, cursor_id=None)),
            ("feedback.get", "feedback", lambda s: feedback.get_feedback_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("permissions.get", "permissions", lambda s: permissions.get_permission_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("permissions.user-value", "permissions", lambda s: permissions.get_permission_by_value(s, TENANT_ID, uuid4(), "view_products")),
            ("permissions.list", "permissions", lambda s: permissions.list_permissions(s, TENANT_ID, user_id=None, limit=10, offset=0)),
            ("agent-tools.list", "agent_tools", lambda s: agent_tools.list_agent_tools(s, TENANT_ID, limit=10, offset=0)),
            ("agent-tools.get", "agent_tools", lambda s: agent_tools.get_tenant_agent_tool_by_name(s, TENANT_ID, "tool")),
            ("users.get", "users", lambda s: users.get_user_by_id(s, TENANT_ID, RESOURCE_ID)),
            ("users.email", "users", lambda s: users.get_user_by_email(s, TENANT_ID, "user@example.com")),
            ("users.list", "users", lambda s: users.list_users(s, TENANT_ID, limit=10, offset=0)),
        ]

        for name, table, operation in checks:
            session = CapturingSession()
            await operation(session)
            assert session.statements, name
            predicate = f"{table}.tenant_id = '{TENANT_ID}'"
            assert all(predicate in compile_sql(statement) for statement in session.statements), name
            if name == "sales.summary":
                assert "orders.tenant_id =" in compile_sql(session.statements[0])

    asyncio.run(run_checks())


def test_cross_tenant_object_reads_and_updates_fail_as_not_found(monkeypatch) -> None:
    async def missing(*_args, **_kwargs):
        return None

    checks = [
        (product_service.product_repository, "get_product_by_id", lambda: product_service.get_product(None, TENANT_ID, RESOURCE_ID)),
        (order_service.order_repository, "get_order_by_id", lambda: order_service.get_order(None, TENANT_ID, RESOURCE_ID)),
        (campaign_service.campaign_repository, "get_campaign_by_id", lambda: campaign_service.get_campaign(None, TENANT_ID, RESOURCE_ID)),
        (campaign_service.campaign_repository, "get_campaign_by_id", lambda: campaign_service.update_campaign(None, TENANT_ID, RESOURCE_ID, CampaignUpdateRequest())),
        (document_service.document_repository, "get_document_by_id", lambda: document_service.get_document(None, TENANT_ID, RESOURCE_ID)),
        (document_service.document_repository, "get_document_by_id", lambda: document_service.update_document(None, TENANT_ID, RESOURCE_ID, DocumentUpdateRequest(title="changed"))),
        (conversation_service.conversation_repository, "get_conversation_by_id", lambda: conversation_service.get_conversation(None, TENANT_ID, RESOURCE_ID)),
        (conversation_service.conversation_repository, "get_conversation_by_id", lambda: conversation_service.update_conversation(None, TENANT_ID, RESOURCE_ID, ConversationUpdateRequest(title="changed"))),
        (feedback_service.feedback_repository, "get_feedback_by_id", lambda: feedback_service.update_feedback(None, TENANT_ID, RESOURCE_ID, FeedbackUpdateRequest(rating=1))),
        (permission_service.permission_repository, "get_permission_by_id", lambda: permission_service.update_permission(None, TENANT_ID, RESOURCE_ID, PermissionUpdateRequest(permission="view_products"))),
        (agent.agent_tool_repository, "get_tenant_agent_tool_by_name", lambda: agent.update_agent_tool(None, TENANT_ID, "tool", AgentToolUpdateRequest(description="changed"))),
        (user_service.user_repository, "get_user_by_id", lambda: user_service.get_user(None, TENANT_ID, RESOURCE_ID)),
        (user_service.user_repository, "get_user_by_id", lambda: user_service.update_user(None, TENANT_ID, RESOURCE_ID, UserUpdateRequest(name="changed"))),
    ]

    for repository, method_name, operation in checks:
        monkeypatch.setattr(repository, method_name, missing)
        with pytest.raises(HTTPException) as error:
            asyncio.run(operation())
        assert error.value.status_code == 404, (repository.__name__, method_name)
