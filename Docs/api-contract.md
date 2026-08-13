# V1/V2 API Contract

## Scope

This contract covers only V1 and V2. The API is split into:

- Protected dashboard APIs for authenticated store owners, marketing managers, team members, and admins.
- Public widget APIs for unauthenticated Shopify storefront customers.

FastAPI is the only API surface called by both the dashboard and widget frontends.

## Shared Pydantic Models

```python
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


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
```

## Auth and Tenant Rules

Protected dashboard APIs:

- Require Supabase Auth JWT unless explicitly marked public.
- Resolve `tenant_id` from the authenticated user and database user record.
- Enforce role and permission checks before accessing business data.

Public widget APIs:

- Do not require customer login.
- Resolve `tenant_id` from `shop_domain` or `shop_id`, `widget_public_key`, and allowed domain validation.
- Must apply rate limiting.
- Must only access public/customer-safe data.

## Authentication Models

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AuthUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    email: EmailStr
    role: Literal["store_owner", "marketing_manager", "team_member", "admin"]


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: Literal["bearer"] = "bearer"
    user: AuthUserResponse
```

## User Models

```python
class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    email: EmailStr
    role: Literal["store_owner", "marketing_manager", "team_member", "admin"]
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    page: PageMeta
```

## Commerce Models

```python
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
    items: list[ProductResponse]
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
    items: list[OrderResponse]
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
    items: list[CampaignResponse]
    page: PageMeta
```

## Document Models

```python
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
    items: list[DocumentResponse]
    page: PageMeta


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
    page: PageMeta
```

Document upload uses `multipart/form-data` with a `file` field, optional `title` field, and optional `visibility` field. Default visibility should be `internal`.

## Conversation and Dashboard Chat Models

```python
class ConversationCreateRequest(BaseModel):
    title: str | None = None


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
    items: list[ConversationResponse]
    page: PageMeta


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender: Literal["user", "customer", "assistant", "system"]
    content: str
    sources: list[SourceRef] = Field(default_factory=list)
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
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
```

## Public Widget Models

```python
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
```

Public widget responses must not include tenant IDs, user IDs, internal document metadata, tool names, sales, orders, campaigns, or private source content.

Public widget chat may use selected public-safe product fields as internal context for `/public/chat` and `/public/chat/stream`. It may only use products where `tenant_id` matches the resolved tenant and `public_visible = true`. It may only expose `id`, `external_product_id`, `name`, `description`, `category`, and `price` through public-safe answer text or source context. V1/V2 should not add a standalone public products endpoint.

## Search Models

```python
class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: Literal["knowledge", "products", "orders", "sales", "campaigns", "all"] = "knowledge"
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    id: UUID | str
    type: str
    title: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    items: list[SearchResult]
```

## Feedback Models

```python
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
```

## Agent Models

```python
class AgentToolResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool = True


class AgentToolListResponse(BaseModel):
    items: list[AgentToolResponse]
```

## Protected Dashboard Endpoints

| Endpoint | Method | Purpose | Auth | Request Body | Response Body | Status Codes |
|---|---:|---|---|---|---|---|
| `/auth/login` | POST | Authenticate dashboard user | Public | `LoginRequest` | `LoginResponse` | 200, 400, 401, 422 |
| `/auth/me` | GET | Return current dashboard user | Required | None | `AuthUserResponse` | 200, 401 |
| `/auth/logout` | POST | End current dashboard session client-side/server-side where supported | Required | None | None | 204, 401 |
| `/users` | GET | List tenant dashboard users | Required: store owner/admin | Query params: `limit`, `offset` | `UserListResponse` | 200, 401, 403 |
| `/users/{user_id}` | GET | Get one tenant dashboard user | Required | None | `UserResponse` | 200, 401, 403, 404 |
| `/products` | GET | List products | Required | Query params: `limit`, `offset`, `status`, `category` | `ProductListResponse` | 200, 401, 403 |
| `/products/{product_id}` | GET | Get product detail | Required | None | `ProductResponse` | 200, 401, 403, 404 |
| `/orders` | GET | List orders | Required | Query params: `limit`, `offset`, `status`, `user_id` | `OrderListResponse` | 200, 401, 403 |
| `/orders/{order_id}` | GET | Get order detail | Required | None | `OrderResponse` | 200, 401, 403, 404 |
| `/sales/summary` | POST | Return simple sales metrics | Required: store owner/team member/admin | `SalesSummaryRequest` | `SalesSummaryResponse` | 200, 401, 403, 422 |
| `/campaigns` | GET | List campaigns | Required: store owner/marketing manager/admin | Query params: `limit`, `offset`, `channel` | `CampaignListResponse` | 200, 401, 403 |
| `/campaigns/{campaign_id}` | GET | Get campaign detail | Required: store owner/marketing manager/admin | None | `CampaignResponse` | 200, 401, 403, 404 |
| `/documents` | GET | List knowledge documents | Required | Query params: `limit`, `offset`, `type`, `status`, `visibility` | `DocumentListResponse` | 200, 401, 403 |
| `/documents` | POST | Upload a document for ingestion | Required: upload documents permission | `multipart/form-data` | `DocumentCreateResponse` | 201, 400, 401, 403, 413, 415, 422 |
| `/documents/{document_id}` | GET | Get document metadata | Required | None | `DocumentResponse` | 200, 401, 403, 404 |
| `/documents/{document_id}/chunks` | GET | List document chunks | Required | Query params: `limit`, `offset` | `DocumentChunkListResponse` | 200, 401, 403, 404 |
| `/conversations` | GET | List dashboard conversations | Required | Query params: `limit`, `offset`, `status` | `ConversationListResponse` | 200, 401, 403 |
| `/conversations` | POST | Create dashboard conversation | Required | `ConversationCreateRequest` | `ConversationResponse` | 201, 401, 403, 422 |
| `/conversations/{conversation_id}` | GET | Get dashboard conversation | Required | None | `ConversationResponse` | 200, 401, 403, 404 |
| `/conversations/{conversation_id}/messages` | GET | List dashboard messages | Required | Query params: `limit`, `offset` | `MessageListResponse` | 200, 401, 403, 404 |
| `/chat` | POST | Send dashboard chat message and receive full response | Required | `ChatRequest` | `ChatResponse` | 200, 401, 403, 422, 500 |
| `/chat/stream` | POST | Send dashboard chat message and stream response | Required | `ChatRequest` | SSE | 200, 401, 403, 422, 500 |
| `/search` | POST | Search internal knowledge and supported business data | Required | `SearchRequest` | `SearchResponse` | 200, 401, 403, 422 |
| `/feedback` | POST | Submit feedback for an assistant message | Required | `FeedbackCreateRequest` | `FeedbackResponse` | 201, 401, 403, 404, 422 |
| `/agent/tools` | GET | List available read-only dashboard agent tools | Required | None | `AgentToolListResponse` | 200, 401, 403 |

## Public Widget Endpoints

| Endpoint | Method | Purpose | Auth | Request Body | Response Body | Status Codes |
|---|---:|---|---|---|---|---|
| `/public/widget/config` | GET | Load widget configuration for a Shopify storefront | Public widget validation | Query params: `shop_id` or `shop_domain`, `widget_public_key` | `PublicWidgetConfigResponse` | 200, 400, 403, 404, 429 |
| `/public/chat` | POST | Send customer widget message and receive full answer | Public widget validation | `PublicChatRequest` | `PublicChatResponse` | 200, 400, 403, 404, 422, 429, 500 |
| `/public/chat/stream` | POST | Send customer widget message and stream answer | Public widget validation | `PublicChatRequest` | SSE | 200, 400, 403, 404, 422, 429, 500 |

Public widget validation means the request must include a valid store identity and widget public key, and the request origin must match the tenant's allowed origins.

## Error Format

All JSON errors use `ErrorResponse`.

Example:

```json
{
  "error": "validation_error",
  "message": "The request body is invalid.",
  "details": [
    {
      "field": "message",
      "message": "Field is required."
    }
  ],
  "request_id": "req_123"
}
```

Common error codes:

- `bad_request`
- `unauthorized`
- `forbidden`
- `not_found`
- `validation_error`
- `unsupported_media_type`
- `payload_too_large`
- `rate_limited`
- `internal_error`

## SSE Event Format for `/chat/stream`

The protected dashboard endpoint accepts `ChatRequest` and returns `text/event-stream`.

### `message_start`

```text
event: message_start
data: {"conversation_id":"...","message_id":"..."}
```

### `token`

```text
event: token
data: {"text":"partial answer text"}
```

### `source`

```text
event: source
data: {"document_id":"...","chunk_id":"...","title":"Return Policy","snippet":"...","score":0.82}
```

### `tool_call`

```text
event: tool_call
data: {"name":"get_sales","status":"started"}
```

### `tool_result`

```text
event: tool_result
data: {"name":"get_sales","status":"completed"}
```

### `message_end`

```text
event: message_end
data: {"conversation_id":"...","message_id":"...","used_tools":["get_sales"]}
```

### `error`

```text
event: error
data: {"error":"internal_error","message":"Unable to complete chat response.","details":[],"request_id":"req_123"}
```

## SSE Event Format for `/public/chat/stream`

The public widget endpoint accepts `PublicChatRequest` and returns `text/event-stream`.

Public widget stream events must not include tool calls, internal document metadata, tenant IDs, user IDs, sales, orders, or campaign data.

### `message_start`

```text
event: message_start
data: {"conversation_id":"...","message_id":"..."}
```

### `token`

```text
event: token
data: {"text":"partial public answer text"}
```

### `source`

```text
event: source
data: {"document_id":"...","chunk_id":"...","title":"Shipping Policy","snippet":"...","score":0.82}
```

### `message_end`

```text
event: message_end
data: {"conversation_id":"...","message_id":"..."}
```

### `error`

```text
event: error
data: {"error":"rate_limited","message":"Please wait before sending another message.","details":[],"request_id":"req_123"}
```
