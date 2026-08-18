"""Placeholder service responses for the documented V1/V2 API shape.

Current status:
- RAG responses are static mock responses.
- Agent behavior is limited to a mock tool list and mock used-tools values.
- Document upload returns metadata only; parsing, chunking, and embeddings are
  not implemented.
- Filters and pagination are accepted by routes but resolved against mock data,
  not persistent storage.

Why placeholder: the current goal is an honest, runnable API contract scaffold
before DB, ingestion, retrieval, and agent orchestration are implemented.
Replace when: approved database repositories, RAG ingestion/retrieval, and agent
tool execution are added.
Target implementation: services that call SQL-backed repositories, real
retrieval over indexed document chunks, validated document processing, and safe
agent orchestration through backend services/tools.
"""

from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from app.features.schemas import (
    AgentToolListResponse,
    AgentToolResponse,
    AuthUserResponse,
    CampaignListResponse,
    CampaignResponse,
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
    LoginRequest,
    LoginResponse,
    MOCK_CHUNK_ID,
    MOCK_CONVERSATION_ID,
    MOCK_DOCUMENT_ID,
    MOCK_MESSAGE_ID,
    MOCK_TENANT_ID,
    MOCK_USER_ID,
    MessageListResponse,
    MessageResponse,
    OrderListResponse,
    OrderResponse,
    PageMeta,
    ProductListResponse,
    ProductResponse,
    PublicChatMessage,
    PublicChatRequest,
    PublicChatResponse,
    PublicSourceRef,
    PublicWidgetConfigResponse,
    SalesSummaryRequest,
    SalesSummaryResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SourceRef,
    UserListResponse,
    UserResponse,
    new_uuid,
    now_utc,
)


def page(limit: int, offset: int, total: int = 1) -> PageMeta:
    return PageMeta(limit=limit, offset=offset, total=total)


def mock_auth_user() -> AuthUserResponse:
    return AuthUserResponse(
        id=MOCK_USER_ID,
        tenant_id=MOCK_TENANT_ID,
        name="Mock Dashboard User",
        email="owner@example.com",
        role="store_owner",
    )


def login(request: LoginRequest) -> LoginResponse:
    return LoginResponse(
        access_token="mock-access-token",
        refresh_token="mock-refresh-token",
        user=AuthUserResponse(
            id=MOCK_USER_ID,
            tenant_id=MOCK_TENANT_ID,
            name="Mock Dashboard User",
            email=request.email,
            role="store_owner",
        ),
    )


def user_response(user_id: UUID = MOCK_USER_ID) -> UserResponse:
    now = now_utc()
    return UserResponse(
        id=user_id,
        tenant_id=MOCK_TENANT_ID,
        name="Mock Dashboard User",
        email="owner@example.com",
        role="store_owner",
        created_at=now,
        updated_at=now,
    )


def list_users(limit: int, offset: int) -> UserListResponse:
    return UserListResponse(items=[user_response()], page=page(limit, offset))


def product_response(product_id: UUID | None = None) -> ProductResponse:
    now = now_utc()
    return ProductResponse(
        id=product_id or new_uuid(),
        tenant_id=MOCK_TENANT_ID,
        external_product_id="shopify-product-1",
        name="Mock Product",
        description="Placeholder product data.",
        category="Demo",
        price=Decimal("19.99"),
        status="active",
        public_visible=True,
        created_at=now,
        updated_at=now,
    )


def list_products(limit: int, offset: int) -> ProductListResponse:
    return ProductListResponse(items=[product_response()], page=page(limit, offset))


def order_response(order_id: UUID | None = None) -> OrderResponse:
    now = now_utc()
    return OrderResponse(
        id=order_id or new_uuid(),
        tenant_id=MOCK_TENANT_ID,
        user_id=MOCK_USER_ID,
        status="paid",
        total_amount=Decimal("49.99"),
        created_at=now,
        updated_at=now,
    )


def list_orders(limit: int, offset: int) -> OrderListResponse:
    return OrderListResponse(items=[order_response()], page=page(limit, offset))


def sales_summary(request: SalesSummaryRequest) -> SalesSummaryResponse:
    return SalesSummaryResponse(
        total_revenue=Decimal("499.90"),
        order_count=10,
        average_order_value=Decimal("49.99"),
    )


def campaign_response(campaign_id: UUID | None = None) -> CampaignResponse:
    now = now_utc()
    return CampaignResponse(
        id=campaign_id or new_uuid(),
        tenant_id=MOCK_TENANT_ID,
        name="Mock Campaign",
        channel="email",
        spend=Decimal("100.00"),
        revenue=Decimal("350.00"),
        roas=Decimal("3.50"),
        created_at=now,
        updated_at=now,
    )


def list_campaigns(limit: int, offset: int) -> CampaignListResponse:
    return CampaignListResponse(items=[campaign_response()], page=page(limit, offset))


def document_response(document_id: UUID = MOCK_DOCUMENT_ID) -> DocumentResponse:
    now = now_utc()
    return DocumentResponse(
        id=document_id,
        tenant_id=MOCK_TENANT_ID,
        title="Mock Policy",
        type="pdf",
        source="mock-policy.pdf",
        visibility="internal",
        status="uploaded",
        chunk_count=1,
        created_at=now,
        updated_at=now,
    )


def create_document(
    filename: str,
    title: str | None,
    visibility: str,
) -> DocumentCreateResponse:
    now = now_utc()
    extension = Path(filename).suffix.lower().lstrip(".")
    document_type = extension if extension in {"pdf", "docx", "txt"} else "txt"
    return DocumentCreateResponse(
        id=MOCK_DOCUMENT_ID,
        tenant_id=MOCK_TENANT_ID,
        title=title or filename,
        type=document_type,
        source=filename,
        visibility=visibility if visibility in {"internal", "public"} else "internal",
        status="uploaded",
        created_at=now,
        updated_at=now,
    )


def list_documents(limit: int, offset: int) -> DocumentListResponse:
    return DocumentListResponse(items=[document_response()], page=page(limit, offset))


def list_document_chunks(limit: int, offset: int) -> DocumentChunkListResponse:
    return DocumentChunkListResponse(
        items=[
            DocumentChunkResponse(
                id=MOCK_CHUNK_ID,
                document_id=MOCK_DOCUMENT_ID,
                chunk_index=0,
                content="Placeholder chunk content.",
                metadata={"visibility": "internal"},
                created_at=now_utc(),
            )
        ],
        page=page(limit, offset),
    )


def conversation_response(
    conversation_id: UUID = MOCK_CONVERSATION_ID,
    request: ConversationCreateRequest | None = None,
) -> ConversationResponse:
    now = now_utc()
    return ConversationResponse(
        id=conversation_id,
        tenant_id=MOCK_TENANT_ID,
        user_id=MOCK_USER_ID,
        surface="dashboard",
        title=request.title if request else "Mock Conversation",
        status="active",
        created_at=now,
        updated_at=now,
    )


def list_conversations(limit: int, offset: int) -> ConversationListResponse:
    return ConversationListResponse(
        items=[conversation_response()],
        page=page(limit, offset),
    )


def source_ref() -> SourceRef:
    return SourceRef(
        document_id=MOCK_DOCUMENT_ID,
        chunk_id=MOCK_CHUNK_ID,
        title="Return Policy",
        snippet="Placeholder source snippet.",
        score=0.82,
    )


def message_response() -> MessageResponse:
    return MessageResponse(
        id=MOCK_MESSAGE_ID,
        conversation_id=MOCK_CONVERSATION_ID,
        sender="assistant",
        content="This is a placeholder dashboard assistant response.",
        sources=[source_ref()],
        created_at=now_utc(),
    )


def list_messages(limit: int, offset: int) -> MessageListResponse:
    return MessageListResponse(items=[message_response()], page=page(limit, offset))


def dashboard_chat(request: ChatRequest) -> ChatResponse:
    conversation_id = request.conversation_id or MOCK_CONVERSATION_ID
    message = message_response().model_copy(update={"conversation_id": conversation_id})
    return ChatResponse(
        conversation_id=conversation_id,
        message=message,
        sources=[source_ref()],
        used_tools=["get_sales"] if request.mode in {"auto", "agent"} else [],
    )


def public_source_ref() -> PublicSourceRef:
    return PublicSourceRef(
        document_id=MOCK_DOCUMENT_ID,
        chunk_id=MOCK_CHUNK_ID,
        title="Shipping Policy",
        snippet="Placeholder public source snippet.",
        score=0.82,
    )


def public_chat(request: PublicChatRequest) -> PublicChatResponse:
    conversation_id = request.conversation_id or MOCK_CONVERSATION_ID
    message = PublicChatMessage(
        id=MOCK_MESSAGE_ID,
        sender="assistant",
        content="This is a placeholder customer-safe response.",
        sources=[public_source_ref()],
        created_at=now_utc(),
    )
    return PublicChatResponse(
        conversation_id=conversation_id,
        message=message,
        sources=[public_source_ref()],
    )


def widget_config(shop_id: str | None, shop_domain: str | None) -> PublicWidgetConfigResponse:
    return PublicWidgetConfigResponse(
        shop_id=shop_id,
        shop_domain=shop_domain or "example-store.myshopify.com",
        store_name="Example Store",
        widget_enabled=True,
        greeting="How can I help?",
        theme={"primary_color": "#111827"},
    )


def search(request: SearchRequest) -> SearchResponse:
    return SearchResponse(
        items=[
            SearchResult(
                id=MOCK_DOCUMENT_ID,
                type=request.scope,
                title="Mock Search Result",
                snippet="Placeholder search snippet.",
                score=0.75,
                metadata={"mock": True},
            )
        ]
    )


def create_feedback(request: FeedbackCreateRequest) -> FeedbackResponse:
    return FeedbackResponse(
        id=new_uuid(),
        user_id=MOCK_USER_ID,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment,
        created_at=now_utc(),
    )


def list_agent_tools() -> AgentToolListResponse:
    return AgentToolListResponse(
        items=[
            AgentToolResponse(
                name="get_products",
                description="Read tenant product data.",
                input_schema={"type": "object", "properties": {}},
            ),
            AgentToolResponse(
                name="get_orders",
                description="Read tenant order data.",
                input_schema={"type": "object", "properties": {}},
            ),
            AgentToolResponse(
                name="get_sales",
                description="Read tenant sales metrics.",
                input_schema={"type": "object", "properties": {}},
            ),
        ]
    )


def sse_payload(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model
