# V1/V2 API Contract

## Scope

This contract covers only V1 and V2. The API supports document-grounded chat, simple business data queries, read-only agent tools, conversations, search, and feedback.

FastAPI is the only API surface called by the frontend.

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
    details: list[ErrorDetail] = []
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
    role: Literal["customer", "store_owner", "marketing_manager", "team_member", "admin"]


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
    role: Literal["customer", "store_owner", "marketing_manager", "team_member", "admin"]
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
    name: str
    description: str | None = None
    category: str | None = None
    status: Literal["active", "inactive", "archived"]
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    page: PageMeta


class OrderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
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
    metadata: dict[str, Any]
    created_at: datetime


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
    page: PageMeta
```

Document upload uses `multipart/form-data` with a `file` field and optional `title` field.

## Conversation and Chat Models

```python
class ConversationCreateRequest(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    user_id: UUID
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
    sender: Literal["user", "assistant", "system"]
    content: str
    sources: list[SourceRef] = []
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
    sources: list[SourceRef] = []
    used_tools: list[str] = []
```

## Search Models

```python
class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: Literal["knowledge", "products", "orders", "sales", "campaigns", "all"] = "knowledge"
    filters: dict[str, Any] = {}


class SearchResult(BaseModel):
    id: UUID | str
    type: str
    title: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] = {}


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
    user_id: UUID
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

## Endpoints

| Endpoint | Method | Purpose | Auth | Request Body | Response Body | Status Codes |
|---|---:|---|---|---|---|---|
| `/auth/login` | POST | Authenticate user | Public | `LoginRequest` | `LoginResponse` | 200, 400, 401, 422 |
| `/auth/me` | GET | Return current user | Required | None | `AuthUserResponse` | 200, 401 |
| `/auth/logout` | POST | End current session client-side/server-side where supported | Required | None | None | 204, 401 |
| `/users` | GET | List tenant users | Required: store owner/admin | Query params: `limit`, `offset` | `UserListResponse` | 200, 401, 403 |
| `/users/{user_id}` | GET | Get one tenant user | Required | None | `UserResponse` | 200, 401, 403, 404 |
| `/products` | GET | List products | Required | Query params: `limit`, `offset`, `status`, `category` | `ProductListResponse` | 200, 401, 403 |
| `/products/{product_id}` | GET | Get product detail | Required | None | `ProductResponse` | 200, 401, 403, 404 |
| `/orders` | GET | List orders | Required | Query params: `limit`, `offset`, `status`, `user_id` | `OrderListResponse` | 200, 401, 403 |
| `/orders/{order_id}` | GET | Get order detail | Required | None | `OrderResponse` | 200, 401, 403, 404 |
| `/sales/summary` | POST | Return simple sales metrics | Required: store owner/team member/admin | `SalesSummaryRequest` | `SalesSummaryResponse` | 200, 401, 403, 422 |
| `/campaigns` | GET | List campaigns | Required: store owner/marketing manager/admin | Query params: `limit`, `offset`, `channel` | `CampaignListResponse` | 200, 401, 403 |
| `/campaigns/{campaign_id}` | GET | Get campaign detail | Required: store owner/marketing manager/admin | None | `CampaignResponse` | 200, 401, 403, 404 |
| `/documents` | GET | List knowledge documents | Required | Query params: `limit`, `offset`, `type`, `status` | `DocumentListResponse` | 200, 401, 403 |
| `/documents` | POST | Upload a document for ingestion | Required: upload documents permission | `multipart/form-data` | `DocumentCreateResponse` | 201, 400, 401, 403, 413, 415, 422 |
| `/documents/{document_id}` | GET | Get document metadata | Required | None | `DocumentResponse` | 200, 401, 403, 404 |
| `/documents/{document_id}/chunks` | GET | List document chunks | Required | Query params: `limit`, `offset` | `DocumentChunkListResponse` | 200, 401, 403, 404 |
| `/conversations` | GET | List user conversations | Required | Query params: `limit`, `offset`, `status` | `ConversationListResponse` | 200, 401, 403 |
| `/conversations` | POST | Create conversation | Required | `ConversationCreateRequest` | `ConversationResponse` | 201, 401, 403, 422 |
| `/conversations/{conversation_id}` | GET | Get conversation | Required | None | `ConversationResponse` | 200, 401, 403, 404 |
| `/conversations/{conversation_id}/messages` | GET | List messages | Required | Query params: `limit`, `offset` | `MessageListResponse` | 200, 401, 403, 404 |
| `/chat` | POST | Send chat message and receive full response | Required | `ChatRequest` | `ChatResponse` | 200, 401, 403, 422, 500 |
| `/chat/stream` | POST | Send chat message and stream response | Required | `ChatRequest` | SSE | 200, 401, 403, 422, 500 |
| `/search` | POST | Search knowledge and supported business data | Required | `SearchRequest` | `SearchResponse` | 200, 401, 403, 422 |
| `/feedback` | POST | Submit feedback for an assistant message | Required | `FeedbackCreateRequest` | `FeedbackResponse` | 201, 401, 403, 404, 422 |
| `/agent/tools` | GET | List available read-only agent tools | Required | None | `AgentToolListResponse` | 200, 401, 403 |

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
- `internal_error`

## SSE Event Format for `/chat/stream`

The endpoint accepts `ChatRequest` and returns `text/event-stream`.

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
