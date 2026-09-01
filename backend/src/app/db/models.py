"""SQLAlchemy models for the PostgreSQL schema."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for database models."""


def uuid_pk() -> MappedColumn[UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


def timestamp_column() -> MappedColumn[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        Index("tenants_shop_id_key", "shop_id", unique=True, postgresql_where=text("shop_id is not null")),
        Index("tenants_shop_domain_key", "shop_domain", unique=True, postgresql_where=text("shop_domain is not null")),
        Index(
            "tenants_widget_public_key_key",
            "widget_public_key",
            unique=True,
            postgresql_where=text("widget_public_key is not null"),
        ),
        Index("tenants_shop_domain_widget_public_key_idx", "shop_domain", "widget_public_key"),
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    shop_id: Mapped[str | None] = mapped_column(Text)
    shop_domain: Mapped[str | None] = mapped_column(Text)
    widget_public_key: Mapped[str | None] = mapped_column(Text)
    widget_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    widget_allowed_origins: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    widget_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    users: Mapped[list[User]] = relationship(back_populates="tenant")
    permissions: Mapped[list[Permission]] = relationship(back_populates="tenant")
    products: Mapped[list[Product]] = relationship(back_populates="tenant")
    orders: Mapped[list[Order]] = relationship(back_populates="tenant")
    sales: Mapped[list[Sale]] = relationship(back_populates="tenant")
    campaigns: Mapped[list[Campaign]] = relationship(back_populates="tenant")
    documents: Mapped[list[Document]] = relationship(back_populates="tenant")
    document_chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="tenant")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="tenant")
    messages: Mapped[list[Message]] = relationship(back_populates="tenant")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="tenant")
    agent_tools: Mapped[list[AgentTool]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role in ('store_owner', 'marketing_manager', 'team_member', 'admin')",
            name="users_role_check",
        ),
        UniqueConstraint("auth_user_id", name="users_auth_user_id_key"),
        UniqueConstraint("tenant_id", "email", name="users_tenant_id_email_key"),
        Index("users_tenant_id_role_idx", "tenant_id", "role"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    auth_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="users")
    permissions: Mapped[list[Permission]] = relationship(back_populates="user")
    orders: Mapped[list[Order]] = relationship(back_populates="user")
    uploaded_documents: Mapped[list[Document]] = relationship(back_populates="uploaded_by_user")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="user")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="user")


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "permission", name="permissions_tenant_id_user_id_permission_key"),
        Index("permissions_tenant_id_permission_idx", "tenant_id", "permission"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permission: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="permissions")
    user: Mapped[User] = relationship(back_populates="permissions")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price is null or price >= 0", name="products_price_check"),
        CheckConstraint("status in ('active', 'inactive', 'archived')", name="products_status_check"),
        Index(
            "products_tenant_id_external_product_id_key",
            "tenant_id",
            "external_product_id",
            unique=True,
            postgresql_where=text("external_product_id is not null"),
        ),
        Index("products_tenant_id_status_idx", "tenant_id", "status"),
        Index("products_tenant_id_category_idx", "tenant_id", "category"),
        Index("products_tenant_id_public_visible_idx", "tenant_id", "public_visible"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    public_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="products")
    sales: Mapped[list[Sale]] = relationship(back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status in ('pending', 'paid', 'fulfilled', 'cancelled', 'refunded')", name="orders_status_check"),
        CheckConstraint("total_amount >= 0", name="orders_total_amount_check"),
        Index("orders_tenant_id_status_idx", "tenant_id", "status"),
        Index("orders_tenant_id_user_id_idx", "tenant_id", "user_id"),
        Index("orders_tenant_id_created_at_idx", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="orders")
    user: Mapped[User | None] = relationship(back_populates="orders")
    sales: Mapped[list[Sale]] = relationship(back_populates="order")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="sales_amount_check"),
        Index("sales_tenant_id_created_at_idx", "tenant_id", "created_at"),
        Index("sales_tenant_id_product_id_idx", "tenant_id", "product_id"),
        Index("sales_tenant_id_order_id_idx", "tenant_id", "order_id"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="sales")
    order: Mapped[Order] = relationship(back_populates="sales")
    product: Mapped[Product | None] = relationship(back_populates="sales")


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("spend >= 0", name="campaigns_spend_check"),
        CheckConstraint("revenue >= 0", name="campaigns_revenue_check"),
        CheckConstraint("roas >= 0", name="campaigns_roas_check"),
        Index("campaigns_tenant_id_channel_idx", "tenant_id", "channel"),
        Index("campaigns_tenant_id_created_at_idx", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    roas: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="campaigns")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("type in ('pdf', 'docx', 'txt', 'markdown', 'notion', 'web', 'csv')", name="documents_type_check"),
        CheckConstraint("visibility in ('internal', 'public')", name="documents_visibility_check"),
        CheckConstraint("status in ('uploaded', 'processing', 'ready', 'failed')", name="documents_status_check"),
        Index("documents_tenant_id_status_idx", "tenant_id", "status"),
        Index("documents_tenant_id_type_idx", "tenant_id", "type"),
        Index("documents_tenant_id_visibility_idx", "tenant_id", "visibility"),
        Index("documents_tenant_id_created_at_idx", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'internal'"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="documents")
    uploaded_by_user: Mapped[User] = relationship(back_populates="uploaded_documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="document_chunks_chunk_index_check"),
        CheckConstraint("visibility in ('internal', 'public')", name="document_chunks_visibility_check"),
        UniqueConstraint("document_id", "chunk_index", name="document_chunks_document_id_chunk_index_key"),
        UniqueConstraint("chroma_vector_id", name="document_chunks_chroma_vector_id_key"),
        Index("document_chunks_tenant_id_document_id_idx", "tenant_id", "document_id"),
        Index("document_chunks_tenant_id_visibility_idx", "tenant_id", "visibility"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    document_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(Text, nullable=False)
    chroma_collection: Mapped[str] = mapped_column(Text, nullable=False)
    chroma_vector_id: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="document_chunks")
    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("surface in ('dashboard', 'widget')", name="conversations_surface_check"),
        CheckConstraint("status in ('active', 'archived')", name="conversations_status_check"),
        Index("conversations_tenant_id_user_id_created_at_idx", "tenant_id", "user_id", "created_at"),
        Index("conversations_tenant_id_surface_created_at_idx", "tenant_id", "surface", "created_at"),
        Index(
            "conversations_tenant_id_visitor_id_idx",
            "tenant_id",
            "visitor_id",
            postgresql_where=text("visitor_id is not null"),
        ),
        Index("conversations_tenant_id_status_idx", "tenant_id", "status"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    visitor_id: Mapped[str | None] = mapped_column(Text)
    shop_domain: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="conversations")
    user: Mapped[User | None] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("sender in ('user', 'customer', 'assistant', 'system')", name="messages_sender_check"),
        Index("messages_tenant_id_conversation_id_created_at_idx", "tenant_id", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    sender: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    used_tools: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="messages")
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="message")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("surface in ('dashboard', 'widget')", name="feedback_surface_check"),
        CheckConstraint("rating between 1 and 5", name="feedback_rating_check"),
        Index("feedback_tenant_id_message_id_idx", "tenant_id", "message_id"),
        Index(
            "feedback_tenant_id_user_id_created_at_idx",
            "tenant_id",
            "user_id",
            "created_at",
            postgresql_where=text("user_id is not null"),
        ),
        Index("feedback_tenant_id_surface_created_at_idx", "tenant_id", "surface", "created_at"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant] = relationship(back_populates="feedback")
    user: Mapped[User | None] = relationship(back_populates="feedback")
    conversation: Mapped[Conversation] = relationship(back_populates="feedback")
    message: Mapped[Message] = relationship(back_populates="feedback")


class AgentTool(Base):
    __tablename__ = "agent_tools"
    __table_args__ = (
        CheckConstraint("read_only", name="agent_tools_read_only_check"),
        Index("agent_tools_tenant_id_name_key", "tenant_id", "name", unique=True),
        Index("agent_tools_tenant_id_read_only_idx", "tenant_id", "read_only"),
    )

    id: Mapped[UUID] = uuid_pk()
    tenant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = timestamp_column()

    tenant: Mapped[Tenant | None] = relationship(back_populates="agent_tools")
