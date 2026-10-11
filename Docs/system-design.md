# V1/V2 System Design

## A. Product Surfaces

AI Commerce Copilot has two product surfaces.

### Owner Dashboard

The Owner Dashboard is the authenticated AI Commerce Copilot web application for store owners, marketing managers, team members, and admins.

It uses protected FastAPI APIs and supports document management, business data queries, dashboard RAG, and internal read-only Agent tools.

### Shopify Customer Chat Widget

The Shopify Customer Chat Widget is embedded inside the merchant's Shopify storefront.

Customers do not register for or log in to AI Commerce Copilot. The widget uses public widget APIs and can only access customer-safe resources.

### API Boundary

Protected dashboard APIs require Supabase Auth JWTs and can access protected tenant resources according to RBAC and ACL rules.

Public widget APIs do not require customer login. They must validate store/widget access and can only access public documents/chunks and public-visible product context.

## B. Authentication

Dashboard authentication uses Supabase Auth.

Flow:

```text
Dashboard frontend
  -> sends JWT bearer token
  -> FastAPI
  -> validates JWT
  -> resolves dashboard user
  -> resolves tenant_id
```

Customers using the Shopify widget do not log in to AI Commerce Copilot.

## C. Authorization

Dashboard authorization uses RBAC for high-level roles and ACL permissions for fine-grained tenant access.

Dashboard roles:

- `store_owner`
- `marketing_manager`
- `team_member`
- `admin`

Dashboard ACL permissions:

- `view_users`
- `manage_users`
- `view_permissions`
- `manage_permissions`
- `view_tenant`
- `manage_tenant`
- `view_products`
- `manage_products`
- `view_orders`
- `view_sales`
- `view_campaigns`
- `manage_campaigns`
- `view_documents`
- `upload_documents`
- `manage_documents`
- `view_conversations`
- `create_conversations`
- `use_dashboard_chat`
- `search_knowledge`
- `submit_feedback`
- `use_agent_tools`
- `connect_shopify_store` (merchant onboarding only)

Tenant isolation is enforced with `tenant_id` on every protected resource.

### Role/Permission Matrix

| Role | Built-in permissions | Stored ACL assignments |
|---|---|---|
| `store_owner` | All listed permissions inside its own tenant | None needed |
| `admin` | `view_users`, `manage_users`, `view_permissions`, `manage_permissions`, `view_tenant`, `manage_tenant`, `view_products`, `manage_products`, `view_orders`, `view_sales`, `view_campaigns`, `view_documents`, `upload_documents`, `manage_documents`, `view_conversations`, `create_conversations`, `use_dashboard_chat`, `search_knowledge`, `submit_feedback`, `use_agent_tools` | None; tenant scoped, not a global administrator |
| `marketing_manager` | `view_users`, `view_products`, `manage_products`, `view_orders`, `view_sales`, `view_campaigns`, `manage_campaigns`, `view_documents`, `upload_documents`, `manage_documents`, `view_conversations`, `create_conversations`, `use_dashboard_chat`, `search_knowledge`, `submit_feedback`, `use_agent_tools` | None |
| `team_member` | `view_users`, `view_products`, `use_dashboard_chat`, `search_knowledge`, `use_agent_tools` | Only `manage_products`, `view_orders`, `view_sales`, `view_campaigns`, `manage_campaigns`, `create_conversations`, `submit_feedback` when assigned in the current tenant |

The API contract's narrower role-only gates still apply to user and permission
listing, tenant administration, sales summaries, and campaign routes. A stored
ACL assignment never overrides those gates. Team members with
`create_conversations` may access only their own conversations; roles with
`view_conversations` may access tenant conversations. Knowledge results and
document sources require `view_documents`; agent tools additionally require
the underlying data permission. `connect_shopify_store` preserves the
authenticated, unlinked store-owner onboarding path and grants no dashboard
resource access.

## D. Public Widget Access Validation

Public widget requests are validated using:

- `shop_domain` or `shop_id`
- `widget_public_key`
- Allowed origin validation
- Rate limiting

FastAPI resolves `tenant_id` from the validated widget/store mapping.

The public widget can only access public/customer-safe resources.

## E. Data Access Boundaries

Dashboard APIs can access protected resources according to RBAC, ACL, and tenant isolation rules.

Public widget APIs can access only:

- Public documents and public chunks.
- Products where `tenant_id` matches the resolved tenant and `public_visible = true`.

Public widget APIs may expose only these product fields:

- `id`
- `external_product_id`
- `name`
- `description`
- `category`
- `price`

Public widget APIs must not expose:

- Orders
- Sales
- Campaigns
- Revenue
- Cost
- Profit
- Internal notes
- Internal documents
- Dashboard users
- Agent tools

For V1/V2, public product lookup is internal context used by `/public/chat` and `/public/chat/stream`. There is no standalone public products endpoint.

## F. RAG Boundary

Dashboard RAG may use internal and public documents according to tenant and permission checks.

Public widget RAG may use only public documents/chunks.

Chroma metadata must include:

- `tenant_id`
- `visibility`

PostgreSQL remains the source of truth for document and chunk metadata.

## G. Agent Boundary

Agent tools are dashboard/internal only in V1/V2.

Agent tools are read-only and must call backend services rather than repositories directly.

Public widget APIs must not expose or call Agent tools.

## H. Main Data Flows

### Owner Dashboard Protected Request Flow

```text
Owner Dashboard
  -> FastAPI protected API
  -> Supabase JWT validation
  -> user and tenant lookup
  -> RBAC/ACL checks
  -> Service
  -> Repository
  -> PostgreSQL
  -> Response
```

### Public Widget Chat Flow

```text
Customer
  -> Shopify Storefront
  -> Embedded Chat Widget
  -> FastAPI public widget API
  -> shop/widget/origin validation
  -> tenant resolution
  -> public RAG retrieval and public-visible product context
  -> customer-safe answer
  -> Widget response
```

### Document Ingestion Flow

```text
Owner Dashboard
  -> FastAPI /documents
  -> Document service
  -> parser
  -> chunker
  -> embeddings
  -> Chroma with tenant_id and visibility metadata
  -> PostgreSQL document/chunk metadata
  -> Response
```

### Dashboard Chat With RAG Flow

```text
Owner Dashboard
  -> FastAPI /chat
  -> Chat service
  -> tenant-scoped RAG retrieval
  -> Chroma
  -> grounded answer with sources
  -> Response
```

### Dashboard Chat With Agent Flow

```text
Owner Dashboard
  -> FastAPI /chat
  -> Chat service
  -> Agent
  -> read-only tool
  -> Backend service
  -> Repository
  -> PostgreSQL
  -> Agent summary
  -> Response
```
