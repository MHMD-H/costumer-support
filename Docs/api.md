# API

## Scope

The API is designed for V1 and V2 only.

FastAPI exposes REST endpoints for normal request and response operations. `/chat/stream` uses Server-Sent Events for streaming assistant responses.

Detailed endpoint contracts are defined in `Docs/api-contract.md`.

## API Rules

- Protocol: HTTPS in deployed environments.
- Local development may use HTTP.
- Format: JSON for normal requests and responses.
- Streaming: SSE for `/chat/stream`.
- Authentication: Supabase Auth JWT bearer token.
- FastAPI is the only backend entry point for the frontend.

## Endpoint Groups

### Authentication

- `/auth/login`
- `/auth/me`
- `/auth/logout`

### Users

- `/users`
- `/users/{user_id}`

### Commerce Data

- `/products`
- `/products/{product_id}`
- `/orders`
- `/orders/{order_id}`
- `/sales/summary`
- `/campaigns`
- `/campaigns/{campaign_id}`

### Knowledge Documents

- `/documents`
- `/documents/{document_id}`
- `/documents/{document_id}/chunks`

### Conversations and Chat

- `/conversations`
- `/conversations/{conversation_id}`
- `/conversations/{conversation_id}/messages`
- `/chat`
- `/chat/stream`

### Search and Feedback

- `/search`
- `/feedback`

### Agent

- `/agent/tools`

V1/V2 agent endpoints are read-only. Action execution and approval endpoints are future work.

## Error Format

All failed JSON responses should use the shared error shape from `Docs/api-contract.md`.
