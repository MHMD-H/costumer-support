# Architecture

## Scope

This architecture covers V1 and V2 only. It separates the owner dashboard experience from the Shopify customer widget experience without designing advanced Shopify app installation, billing, webhooks, or V3-V6 features.

## Product Surfaces

### Owner Dashboard

The owner dashboard is the authenticated AI Commerce Copilot web application.

Users:

- Store owners
- Marketing managers
- Team members
- Admins

Responsibilities:

- Manage documents and document visibility.
- View business data.
- Configure the customer chatbot widget.
- Use internal AI chat.
- Use read-only agent tools.

### Shopify Customer Chat Widget

The customer chat widget is embedded inside the merchant's Shopify storefront.

Users:

- Store customers

Responsibilities:

- Send customer questions to public widget APIs.
- Display customer-safe answers.
- Display public-safe sources when available.

Customers do not authenticate with AI Commerce Copilot.

## Main Components

### Dashboard Frontend

The dashboard frontend is a Next.js application for internal merchant users.

Responsibilities:

- Render dashboard pages and forms.
- Send authenticated requests to protected FastAPI APIs.
- Display internal chat responses and source citations.
- Display products, orders, sales, campaigns, documents, conversations, and feedback workflows.
- Configure public widget settings.

The dashboard frontend must only call protected FastAPI APIs.

### Shopify Widget Frontend

The widget frontend is embedded in the Shopify storefront.

Responsibilities:

- Load public widget configuration.
- Send public chat requests.
- Include `shop_domain` or `shop_id`, `widget_public_key`, and optional page/product context.
- Display customer-safe answers.

The widget must only call public widget FastAPI APIs.

### FastAPI Backend

FastAPI is the main entry point and orchestrator for both surfaces.

Responsibilities:

- Expose protected dashboard REST and SSE endpoints.
- Expose public widget REST and SSE endpoints.
- Validate Supabase JWT bearer tokens for protected dashboard APIs.
- Resolve dashboard tenant context from the authenticated user and database user record.
- Resolve widget tenant context from Shopify store identity and widget configuration.
- Validate allowed origins/domains for widget calls.
- Apply rate limiting to public widget endpoints.
- Enforce role and permission checks for protected resources.
- Coordinate services, repositories, RAG, and Agent flows.
- Return consistent success and error responses.

### Services

Services contain application business logic.

Responsibilities:

- Validate application rules.
- Coordinate repositories.
- Call RAG or Agent interfaces when needed.
- Keep route handlers thin.
- Enforce customer-safe retrieval rules for widget chat.

### Repositories

Repositories are responsible for PostgreSQL access.

Responsibilities:

- Query and persist structured data.
- Apply tenant-scoped filters.
- Hide SQL details from services.

### RAG Package

The RAG package handles document knowledge workflows.

Responsibilities:

- Parse uploaded documents.
- Split text into chunks.
- Generate embeddings.
- Store and retrieve vectors from Chroma.
- Return retrieved chunks with source metadata.
- Filter retrieval by tenant and document visibility.
- Generate grounded answers when called by backend services.

### Agent Package

The Agent package handles simple tool orchestration for authenticated dashboard users in V1/V2.

Responsibilities:

- Decide whether an internal dashboard question needs structured business data.
- Select one or more read-only tools.
- Call tools through backend service interfaces.
- Summarize results in natural language.
- Avoid business-changing actions in V1/V2.

The public Shopify widget must not access internal agent tools.

### PostgreSQL

PostgreSQL stores structured data:

- Tenants and widget configuration.
- Dashboard users and permissions.
- Products, orders, sales, and campaigns.
- Documents and document chunk metadata.
- Conversations and messages.
- Feedback.

### Chroma

Chroma stores vector embeddings for document chunks. PostgreSQL remains the source of truth for document metadata, tenant ownership, visibility, and chunk records.

## Dependency Direction

Owner dashboard flow:

```text
Dashboard Frontend -> FastAPI protected routes -> Services -> Repositories -> PostgreSQL
```

Public widget flow:

```text
Shopify Widget -> FastAPI public widget routes -> Widget chat service -> RAG -> Chroma
```

Internal knowledge flow:

```text
FastAPI services -> RAG package -> Chroma
```

Internal business tool flow:

```text
FastAPI services -> Agent package -> Backend service/tool interface -> Repositories -> PostgreSQL
```

## Tenant Resolution

### Protected Dashboard APIs

For protected dashboard APIs:

1. FastAPI validates the Supabase Auth JWT.
2. FastAPI resolves the authenticated user.
3. FastAPI loads the user record from PostgreSQL.
4. `tenant_id` is resolved from the database user record.
5. Role and permission checks are applied.

### Public Widget APIs

For public Shopify widget APIs:

1. The widget sends `shop_domain` or `shop_id`.
2. The widget sends `widget_public_key`.
3. FastAPI validates the request origin against the tenant's allowed origins.
4. FastAPI resolves `tenant_id` from the store identity and widget key.
5. The public chat service limits retrieval to public/customer-safe data.

## Authentication and Authorization

Authentication uses Supabase Auth JWTs for dashboard users only.

Dashboard roles:

- Store Owner
- Marketing Manager
- Team Member
- Admin

Customers are not dashboard users and should not be required to log in to AI Commerce Copilot.

Tenant isolation must be applied to all tenant-owned resources.

## Security Boundaries

Public widget APIs must never expose:

- Sales
- Orders
- Campaigns
- Internal agent tools
- Internal/private documents
- User, team, or admin data

Public widget APIs may access only:

- Public documents.
- Customer-facing product information.
- Approved shipping, return, warranty, and policy content.

## Simplicity Rules

- Do not introduce advanced Shopify OAuth installation in V1/V2.
- Do not add Shopify billing in V1/V2.
- Do not add Shopify webhook processing in V1/V2.
- Do not introduce background workers until document ingestion becomes slow enough to require them.
- Do not implement business-changing agent actions in V1/V2.
- Keep the RAG and Agent packages callable from backend services.
