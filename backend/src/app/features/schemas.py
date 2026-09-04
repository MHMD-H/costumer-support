"""Shared API schemas for the V1/V2 FastAPI contract."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

EmailStr = Annotated[
    str,
    Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
]

DashboardRole = Literal["store_owner", "marketing_manager", "team_member", "admin"]


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str | None = None


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class SourceRef(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    snippet: str
    score: float | None = None


class AuthUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    email: EmailStr
    role: DashboardRole


class UserResponse(AuthUserResponse):
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse] = Field(default_factory=list)
    page: PageMeta


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    role: DashboardRole | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    shop_id: str | None = None
    shop_domain: str | None = None
    widget_public_key: str | None = None
    widget_enabled: bool
    widget_allowed_origins: list[Any] = Field(default_factory=list)
    widget_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    shop_id: str | None = None
    shop_domain: str | None = None
    widget_public_key: str | None = None
    widget_enabled: bool | None = None
    widget_allowed_origins: list[Any] | None = None
    widget_settings: dict[str, Any] | None = None


class PermissionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    permission: str
    created_at: datetime


class PermissionListResponse(BaseModel):
    items: list[PermissionResponse] = Field(default_factory=list)
    page: PageMeta


class PermissionUpdateRequest(BaseModel):
    permission: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: Literal["bearer"] = "bearer"
    user: AuthUserResponse


class ProductResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    external_product_id: str | None = None
    name: str
    description: str | None = None
    category: str | None = None
    price: Decimal | None = None
    status: Literal["active", "inactive", "archived"]
    public_visible: bool = False
    created_at: datetime
    updated_at: datetime


class PublicProductRef(BaseModel):
    id: UUID
    external_product_id: str | None = None
    name: str
    description: str | None = None
    category: str | None = None
    price: Decimal | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse] = Field(default_factory=list)
    page: PageMeta


class OrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    status: Literal["pending", "paid", "fulfilled", "cancelled", "refunded"]
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderResponse] = Field(default_factory=list)
    page: PageMeta


class SalesSummaryRequest(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    product_id: UUID | None = None


class SalesSummaryResponse(BaseModel):
    total_revenue: Decimal
    order_count: int
    average_order_value: Decimal


class CampaignResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    channel: str
    spend: Decimal
    revenue: Decimal
    roas: Decimal
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse] = Field(default_factory=list)
    page: PageMeta


class CampaignCreateRequest(BaseModel):
    name: str
    channel: str
    spend: Decimal
    revenue: Decimal
    roas: Decimal


class CampaignUpdateRequest(BaseModel):
    name: str | None = None
    channel: str | None = None
    spend: Decimal | None = None
    revenue: Decimal | None = None
    roas: Decimal | None = None


class DocumentCreateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    title: str
    type: Literal["pdf", "docx", "txt"]
    source: str
    visibility: Literal["internal", "public"]
    status: Literal["uploaded", "processing", "ready", "failed"]
    created_at: datetime
    updated_at: datetime


class DocumentResponse(DocumentCreateResponse):
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse] = Field(default_factory=list)
    page: PageMeta


class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    visibility: Literal["internal", "public"] | None = None
    status: Literal["uploaded", "processing", "ready", "failed"] | None = None
    metadata: dict[str, Any] | None = None


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse] = Field(default_factory=list)
    page: PageMeta


class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationUpdateRequest(BaseModel):
    title: str | None = None
    status: Literal["active", "archived"] | None = None


class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    surface: Literal["dashboard", "widget"]
    title: str | None = None
    status: Literal["active", "archived"]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse] = Field(default_factory=list)
    page: PageMeta


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender: Literal["user", "customer", "assistant", "system"]
    content: str
    sources: list[SourceRef] = Field(default_factory=list)
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse] = Field(default_factory=list)
    page: PageMeta


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    mode: Literal["auto", "rag", "agent"] = "auto"


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: MessageResponse
    sources: list[SourceRef] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)


class PublicWidgetConfigRequest(BaseModel):
    shop_id: str | None = None
    shop_domain: str | None = None
    widget_public_key: str


class PublicWidgetConfigResponse(BaseModel):
    shop_id: str | None = None
    shop_domain: str
    store_name: str
    widget_enabled: bool
    greeting: str | None = None
    theme: dict[str, Any] = Field(default_factory=dict)


class PublicSourceRef(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    snippet: str
    score: float | None = None


class PublicChatRequest(BaseModel):
    shop_id: str | None = None
    shop_domain: str | None = None
    widget_public_key: str
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    page_url: str | None = None
    product_id: str | None = None


class PublicChatMessage(BaseModel):
    id: UUID
    sender: Literal["assistant"]
    content: str
    sources: list[PublicSourceRef] = Field(default_factory=list)
    created_at: datetime


class PublicChatResponse(BaseModel):
    conversation_id: UUID
    message: PublicChatMessage
    sources: list[PublicSourceRef] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: Literal["knowledge", "products", "orders", "sales", "campaigns", "all"] = (
        "knowledge"
    )
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    id: UUID | str
    type: str
    title: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    items: list[SearchResult] = Field(default_factory=list)


class FeedbackCreateRequest(BaseModel):
    conversation_id: UUID
    message_id: UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    conversation_id: UUID
    message_id: UUID
    rating: int
    comment: str | None = None
    created_at: datetime


class FeedbackUpdateRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class AgentToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True


class AgentToolListResponse(BaseModel):
    items: list[AgentToolResponse] = Field(default_factory=list)


class AgentToolUpdateRequest(BaseModel):
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    read_only: bool | None = None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


MOCK_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
MOCK_USER_ID = UUID("22222222-2222-2222-2222-222222222222")
MOCK_CONVERSATION_ID = UUID("33333333-3333-3333-3333-333333333333")
MOCK_MESSAGE_ID = UUID("44444444-4444-4444-4444-444444444444")
MOCK_DOCUMENT_ID = UUID("55555555-5555-5555-5555-555555555555")
MOCK_CHUNK_ID = UUID("66666666-6666-6666-6666-666666666666")


def new_uuid() -> UUID:
    return uuid4()
