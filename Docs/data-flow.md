# V1/V2 Data Flow

## Purpose

This document explains how the main project parts interact in V1/V2. It keeps the architecture simple and focused on implementation.

There are two product surfaces:

- Owner Dashboard: authenticated SaaS dashboard for merchant internal users.
- Shopify Customer Chat Widget: embedded storefront chatbot for customers.

FastAPI is the main entry point and orchestrator for both surfaces.

## Component Responsibilities

### Owner Dashboard

Renders the internal AI Commerce Copilot dashboard and calls protected FastAPI APIs.

### Shopify Widget

Runs inside the merchant's Shopify storefront and calls public widget FastAPI APIs.

### FastAPI

Validates requests, authenticates dashboard users, validates public widget requests, resolves tenants, checks permissions, and coordinates services.

### Service

Contains application logic for one feature area, such as products, chat, documents, widget config, or sales.

### Repository

Reads and writes PostgreSQL data for a service.

### PostgreSQL

Stores structured data, tenant ownership, dashboard users, widget configuration, conversations, document metadata, and feedback.

### RAG

Parses documents, chunks text, embeds chunks, retrieves relevant context, filters by visibility, and helps generate grounded answers.

### Chroma

Stores vector embeddings for document chunks.

### Agent

Selects and calls read-only tools for dashboard business questions, then summarizes the results.

## 1. Owner Dashboard Flow

Example: store owner views products or asks an internal business question.

```text
Store Owner
  -> AI Commerce Copilot Dashboard
  -> FastAPI protected API
  -> Services / Repositories / RAG / Agent
  -> PostgreSQL / Chroma
  -> FastAPI response
  -> Dashboard
```

Flow:

1. The internal user signs in through Supabase Auth.
2. The dashboard sends a request to a protected FastAPI API with a bearer token.
3. FastAPI validates the JWT.
4. FastAPI loads the database user record and resolves `tenant_id`.
5. FastAPI checks role and permissions.
6. Services coordinate repositories, RAG, or Agent behavior.
7. PostgreSQL and Chroma are accessed only through backend code.
8. FastAPI returns a response to the dashboard.

## 2. Customer Widget Flow

Example: a customer asks a return-policy question inside a Shopify store.

```text
Customer
  -> Shopify Storefront
  -> Embedded Chat Widget
  -> FastAPI public widget API
  -> Tenant resolved from shop_domain/widget key
  -> Customer-safe RAG retrieval
  -> Response returned to widget
```

Flow:

1. The customer opens the merchant's Shopify storefront.
2. The embedded widget loads its public configuration.
3. The widget sends `shop_domain` or `shop_id`, `widget_public_key`, and the customer message to FastAPI.
4. FastAPI validates the widget key and request origin against allowed domains.
5. FastAPI resolves the tenant/store.
6. The public chat service retrieves only public/customer-safe context.
7. RAG searches Chroma with `tenant_id` and `visibility = public`.
8. When useful, the public chat service may add public-visible product context from products where `tenant_id` matches and `public_visible = true`.
9. Only product `id`, `external_product_id`, `name`, `description`, `category`, and `price` may be used in public widget answers.
10. The LLM generates a customer-safe answer.
11. FastAPI returns the answer and public-safe sources to the widget.

Customers do not log in to AI Commerce Copilot.

## 3. Normal Dashboard Database Request Flow

Example: listing products or retrieving an order in the owner dashboard.

```text
Dashboard
  -> FastAPI protected route
  -> Service
  -> Repository
  -> PostgreSQL
  -> Repository
  -> Service
  -> FastAPI response
  -> Dashboard
```

Flow:

1. The dashboard sends a request to FastAPI.
2. FastAPI validates the JWT and resolves the current tenant from the database user record.
3. FastAPI calls the relevant service.
4. The service applies business rules.
5. The repository queries PostgreSQL with a tenant filter.
6. The service returns the result.
7. FastAPI sends the response to the dashboard.

## 4. Dashboard Chat With RAG Flow

Example: store owner asks about an internal policy document.

```text
Dashboard
  -> FastAPI /chat
  -> Chat service
  -> RAG retrieval
  -> Chroma
  -> RAG retrieval
  -> LLM answer
  -> Chat service stores messages and sources
  -> FastAPI response with sources
  -> Dashboard
```

Flow:

1. The dashboard sends a chat message to `/chat`.
2. FastAPI authenticates the user and resolves the tenant.
3. The chat service stores the user message.
4. The chat service asks RAG for relevant tenant context.
5. RAG searches Chroma using tenant and permission-safe filters.
6. RAG returns relevant chunks and source metadata.
7. The LLM generates a grounded answer from the retrieved context.
8. The chat service stores the assistant message and sources.
9. FastAPI returns the answer and sources to the dashboard.

For `/chat/stream`, the same flow applies, but FastAPI streams events as the answer is generated.

## 5. Dashboard Chat With Agent Tool Flow

Example: store owner asks, "What were my sales this month?"

```text
Dashboard
  -> FastAPI /chat
  -> Chat service
  -> Agent
  -> Tool
  -> Backend service
  -> Repository
  -> PostgreSQL
  -> Backend service
  -> Tool result
  -> Agent summary
  -> Chat service stores messages and used tools
  -> FastAPI response
  -> Dashboard
```

Flow:

1. The dashboard sends a chat message to `/chat`.
2. FastAPI authenticates the user and resolves the tenant.
3. The chat service decides the request needs internal business data.
4. The Agent selects one or more read-only tools.
5. Each tool calls a backend service instead of querying PostgreSQL directly.
6. The backend service uses a repository to query PostgreSQL with tenant filters.
7. The Agent summarizes the tool results.
8. The chat service stores the assistant message and used tool names.
9. FastAPI returns the summary to the dashboard.

In V1/V2, agent tools are dashboard-only and read-only. They do not create, update, or delete business resources.

## 6. Document Ingestion Flow

Example: store owner uploads a PDF policy document and marks it public or internal.

```text
Dashboard uploads document
  -> FastAPI /documents
  -> Document service
  -> RAG ingestion
  -> Parser
  -> Chunker
  -> Embeddings
  -> Chroma
  -> Document metadata and chunk metadata stored in PostgreSQL
  -> FastAPI response
  -> Dashboard
```

Flow:

1. The dashboard uploads a PDF, DOCX, or TXT file to FastAPI.
2. FastAPI authenticates the user and checks upload permission.
3. The document service creates a document metadata record.
4. The document is marked `internal` by default unless the dashboard user chooses `public`.
5. RAG ingestion parses the file text.
6. The chunker splits text into smaller chunks.
7. The embedding component generates a vector for each chunk.
8. Chroma stores each vector with tenant, source, and visibility metadata.
9. PostgreSQL stores document metadata and chunk metadata.
10. The document status becomes `ready` or `failed`.
11. FastAPI returns the document status to the dashboard.

## Boundary Rules

- Dashboard frontend calls only protected FastAPI APIs.
- Shopify widget calls only public widget FastAPI APIs.
- FastAPI coordinates all authentication, widget validation, authorization, and tenant isolation.
- Services call repositories for PostgreSQL access.
- RAG talks to Chroma through a retrieval or ingestion interface.
- Agent tools call backend services, not repositories directly.
- Public widget APIs never expose sales, orders, campaigns, internal tools, private documents, or user/team/admin data.
- Public widget APIs may use only public documents/chunks and public-visible product fields as customer-safe context.
- PostgreSQL stores structured data and metadata.
- Chroma stores vector embeddings.
