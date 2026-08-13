# API

## Scope

The API is designed for V1 and V2 only.

FastAPI exposes two API groups:

- Protected dashboard APIs for authenticated owner/team/admin users.
- Public widget APIs for the embedded Shopify customer chatbot.

Detailed endpoint contracts are defined in `Docs/api-contract.md`.

## API Rules

- Protocol: HTTPS in deployed environments.
- Local development may use HTTP.
- Format: JSON for normal requests and responses.
- Streaming: SSE for `/chat/stream` and `/public/chat/stream`.
- FastAPI is the only backend entry point.
- The dashboard frontend calls only protected FastAPI APIs.
- The Shopify widget calls only public widget FastAPI APIs.

## Protected Dashboard APIs

Protected dashboard APIs require Supabase Auth JWT bearer tokens.

Tenant context is resolved from the authenticated user and the database user record.

These APIs may access business data depending on role and permissions.

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

V1/V2 agent endpoints are read-only and dashboard-only. Action execution and approval endpoints are future work.

## Public Widget APIs

Public widget APIs are used only by the embedded Shopify customer chatbot.

They do not require customer login to AI Commerce Copilot. They must still resolve the tenant safely using store identity, widget key, and allowed domain validation.

Public widget APIs must not expose sales, orders, campaigns, internal tools, private documents, or user/team/admin data.

### Widget

- `/public/widget/config`
- `/public/chat`
- `/public/chat/stream`

## Error Format

All failed JSON responses should use the shared error shape from `Docs/api-contract.md`.
