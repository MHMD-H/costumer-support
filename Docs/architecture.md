# Architecture

## Scope

This architecture covers V1 and V2 only. It keeps future versions possible without designing V3-V6 in detail.

## Main Components

### Frontend

The frontend is a Next.js application used by customers, store owners, and marketing managers.

Responsibilities:

- Render pages and forms.
- Send authenticated requests to FastAPI.
- Display chat responses and source citations.
- Display products, orders, sales, campaigns, documents, conversations, and feedback workflows.

The frontend must only call FastAPI. It must not call PostgreSQL, Chroma, the RAG package, or the Agent package directly.

### FastAPI Backend

FastAPI is the main entry point and orchestrator.

Responsibilities:

- Expose REST endpoints.
- Stream chat responses through SSE.
- Validate JWT bearer tokens.
- Resolve the current user and tenant.
- Enforce role and permission checks.
- Coordinate services, repositories, RAG, and Agent flows.
- Return consistent success and error responses.

### Services

Services contain application business logic.

Responsibilities:

- Validate application rules.
- Coordinate repositories.
- Call RAG or Agent interfaces when needed.
- Keep route handlers thin.

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
- Generate grounded answers when called by backend services.

### Agent Package

The Agent package handles simple tool orchestration for V1/V2.

Responsibilities:

- Decide whether a question needs structured business data.
- Select one or more read-only tools.
- Call tools through backend service interfaces.
- Summarize results in natural language.
- Avoid business-changing actions in V1/V2.

### PostgreSQL

PostgreSQL stores structured data:

- Tenants and users.
- Products, orders, sales, and campaigns.
- Documents and document chunk metadata.
- Conversations and messages.
- Feedback.

### Chroma

Chroma stores vector embeddings for document chunks. PostgreSQL remains the source of truth for document metadata, tenant ownership, and chunk records.

## Dependency Direction

The intended dependency flow is:

Frontend -> FastAPI routes -> Services -> Repositories -> PostgreSQL

For chat and knowledge flows:

FastAPI services -> RAG package -> Chroma

For business tool flows:

FastAPI services -> Agent package -> Backend service/tool interface -> Repositories -> PostgreSQL

## Authentication and Authorization

Authentication uses Supabase Auth JWTs transported as bearer tokens.

FastAPI validates the token, resolves the user, resolves the tenant, and enforces permissions before protected resources are accessed.

V1/V2 roles:

- Customer
- Store Owner
- Marketing Manager
- Team Member
- Admin

Tenant isolation must be applied to all tenant-owned resources.

## Simplicity Rules

- Do not introduce background workers until document ingestion becomes slow enough to require them.
- Do not add external commerce integrations for V1/V2.
- Do not implement business-changing agent actions in V1/V2.
- Keep the RAG and Agent packages callable from backend services.
