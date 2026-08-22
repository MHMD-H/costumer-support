# V1/V2 Database Schema

## Scope

This schema supports V1 and V2 only:

- Tenant isolation and simple Shopify widget mapping.
- Dashboard users and permissions.
- Products, orders, sales, and campaigns for the owner dashboard.
- Public and internal document metadata.
- Dashboard and widget conversations.
- Feedback.
- Read-only dashboard agent tool metadata.

PostgreSQL stores structured data and metadata. Chroma stores vector embeddings for document chunks.

This schema does not design advanced Shopify OAuth installation, billing, or webhook processing.

## PostgreSQL Conventions

- Primary keys use `uuid`.
- Tenant-owned tables include `tenant_id`.
- Timestamps use `timestamptz`.
- Money values use `numeric(12, 2)`.
- JSON metadata uses `jsonb`.
- All tenant-scoped queries must filter by `tenant_id`.
- Public widget lookups must validate store identity, widget key, and allowed origin before resolving `tenant_id`.

## Tables

### tenants

Stores businesses using the platform and the simple Shopify/widget mapping needed for V1/V2.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `name` | `text` | Not null |
| `shop_id` | `text` | Nullable, unique |
| `shop_domain` | `text` | Nullable, unique |
| `widget_public_key` | `text` | Nullable, unique |
| `widget_enabled` | `boolean` | Not null, default `true` |
| `widget_allowed_origins` | `jsonb` | Not null, default `[]` |
| `widget_settings` | `jsonb` | Not null, default `{}` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `shop_id` where `shop_id is not null`.
- Unique index on `shop_domain` where `shop_domain is not null`.
- Unique index on `widget_public_key` where `widget_public_key is not null`.
- Index on `(shop_domain, widget_public_key)`.

Relationship notes:

- A tenant owns dashboard users, products, orders, sales, campaigns, documents, conversations, feedback, and agent metadata.
- `widget_public_key` identifies the public widget but is not a private API secret.
- `widget_allowed_origins` contains allowed storefront origins, such as `https://example-store.myshopify.com`.

### users

Stores authenticated dashboard users mapped to Supabase Auth users.

Customers using the Shopify widget are not stored here and do not authenticate with AI Commerce Copilot.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `auth_user_id` | `uuid` | Unique, not null |
| `name` | `text` | Not null |
| `email` | `text` | Not null |
| `role` | `text` | Not null, check in `store_owner`, `marketing_manager`, `team_member`, `admin` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `auth_user_id`.
- Unique index on `(tenant_id, email)`.
- Index on `(tenant_id, role)`.

Relationship notes:

- Store owners, marketing managers, team members, and admins access tenant resources according to role and permissions.

### permissions

Stores optional fine-grained tenant permissions for dashboard users.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, not null |
| `permission` | `text` | Not null |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `(tenant_id, user_id, permission)`.
- Index on `(tenant_id, permission)`.

Relationship notes:

- RBAC gives broad dashboard access.
- This table supports simple ACL checks without introducing a complex policy engine.

### products

Stores product data.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `external_product_id` | `text` | Nullable |
| `name` | `text` | Not null |
| `description` | `text` | Nullable |
| `category` | `text` | Nullable |
| `price` | `numeric(12, 2)` | Nullable, check `price >= 0` when not null |
| `status` | `text` | Not null, check in `active`, `inactive`, `archived` |
| `public_visible` | `boolean` | Not null, default `false` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `(tenant_id, external_product_id)` where `external_product_id is not null`.
- Index on `(tenant_id, status)`.
- Index on `(tenant_id, category)`.
- Index on `(tenant_id, public_visible)`.

Relationship notes:

- Protected dashboard APIs can access tenant products according to permissions.
- Public widget APIs can only use products marked `public_visible = true`.
- Public widget chat may use product rows only when `tenant_id` matches the resolved tenant.
- Public widget chat may expose only these product fields: `id`, `external_product_id`, `name`, `description`, `category`, and `price`.
- Public widget chat must never expose product cost, profit, internal notes, orders, sales, campaigns, revenue, dashboard users, or agent tools.
- V1/V2 do not include a standalone public products endpoint; public product lookup is internal context for `/public/chat` and `/public/chat/stream`.

### orders

Stores order headers for dashboard use.

Orders are private business data and must never be exposed through public widget APIs.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, nullable |
| `status` | `text` | Not null, check in `pending`, `paid`, `fulfilled`, `cancelled`, `refunded` |
| `total_amount` | `numeric(12, 2)` | Not null, check `total_amount >= 0` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, status)`.
- Index on `(tenant_id, user_id)`.
- Index on `(tenant_id, created_at)`.

Relationship notes:

- V1/V2 keep orders simple. Order line items can be added later if product-level order detail is required.
- Shopify storefront customers are not represented as dashboard `users`.

### sales

Stores sales records used for simple dashboard metrics.

Sales are private business data and must never be exposed through public widget APIs.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `order_id` | `uuid` | Foreign key to `orders.id`, not null |
| `product_id` | `uuid` | Foreign key to `products.id`, nullable |
| `amount` | `numeric(12, 2)` | Not null, check `amount >= 0` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, created_at)`.
- Index on `(tenant_id, product_id)`.
- Index on `(tenant_id, order_id)`.

Relationship notes:

- `product_id` is nullable so order-level sales summaries can exist before detailed line-item modeling.

### campaigns

Stores simple marketing campaign metrics for dashboard use.

Campaigns are private business data and must never be exposed through public widget APIs.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `name` | `text` | Not null |
| `channel` | `text` | Not null |
| `spend` | `numeric(12, 2)` | Not null, check `spend >= 0` |
| `revenue` | `numeric(12, 2)` | Not null, check `revenue >= 0` |
| `roas` | `numeric(12, 4)` | Not null, check `roas >= 0` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, channel)`.
- Index on `(tenant_id, created_at)`.

### documents

Stores document metadata.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `uploaded_by_user_id` | `uuid` | Foreign key to `users.id`, not null |
| `title` | `text` | Not null |
| `type` | `text` | Not null, check in `pdf`, `docx`, `txt`, `markdown`, `notion`, `web`, `csv` |
| `source` | `text` | Not null |
| `visibility` | `text` | Not null, default `internal`, check in `internal`, `public` |
| `status` | `text` | Not null, check in `uploaded`, `processing`, `ready`, `failed` |
| `metadata` | `jsonb` | Not null, default `{}` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, status)`.
- Index on `(tenant_id, type)`.
- Index on `(tenant_id, visibility)`.
- Index on `(tenant_id, created_at)`.

Relationship notes:

- `internal` documents are available only to protected dashboard APIs.
- `public` documents may be used by public widget APIs.
- Actual uploaded file storage can be local in development and replaced later.

### document_chunks

Stores chunk metadata and optional chunk text for source display.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `document_id` | `uuid` | Foreign key to `documents.id`, not null |
| `chunk_index` | `integer` | Not null, check `chunk_index >= 0` |
| `content` | `text` | Not null |
| `visibility` | `text` | Not null, check in `internal`, `public` |
| `chroma_collection` | `text` | Not null |
| `chroma_vector_id` | `text` | Unique, not null |
| `metadata` | `jsonb` | Not null, default `{}` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `(document_id, chunk_index)`.
- Unique index on `chroma_vector_id`.
- Index on `(tenant_id, document_id)`.
- Index on `(tenant_id, visibility)`.

Relationship notes:

- Chroma stores the embedding vector.
- PostgreSQL stores the tenant, document relationship, visibility, chunk text, and source metadata.
- Public widget retrieval must filter by `tenant_id` and `visibility = 'public'`.
- Returned chunk IDs should be verified against PostgreSQL before source display.

### conversations

Stores dashboard and widget chat conversation metadata.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, nullable |
| `surface` | `text` | Not null, check in `dashboard`, `widget` |
| `visitor_id` | `text` | Nullable |
| `shop_domain` | `text` | Nullable |
| `title` | `text` | Nullable |
| `status` | `text` | Not null, check in `active`, `archived` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, user_id, created_at)`.
- Index on `(tenant_id, surface, created_at)`.
- Index on `(tenant_id, visitor_id)` where `visitor_id is not null`.
- Index on `(tenant_id, status)`.

Relationship notes:

- Dashboard conversations have `surface = 'dashboard'` and a `user_id`.
- Widget conversations have `surface = 'widget'`, no dashboard `user_id`, and may include a `visitor_id` or `shop_domain`.

### messages

Stores dashboard and widget messages.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `conversation_id` | `uuid` | Foreign key to `conversations.id`, not null |
| `sender` | `text` | Not null, check in `user`, `customer`, `assistant`, `system` |
| `content` | `text` | Not null |
| `sources` | `jsonb` | Not null, default `[]` |
| `used_tools` | `jsonb` | Not null, default `[]` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, conversation_id, created_at)`.

Relationship notes:

- Dashboard messages may include internal sources and read-only tool names.
- Widget messages must include only public-safe sources and no internal tool details.

### feedback

Stores feedback on assistant messages.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, nullable |
| `conversation_id` | `uuid` | Foreign key to `conversations.id`, not null |
| `message_id` | `uuid` | Foreign key to `messages.id`, not null |
| `surface` | `text` | Not null, check in `dashboard`, `widget` |
| `rating` | `integer` | Not null, check `rating between 1 and 5` |
| `comment` | `text` | Nullable |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, message_id)`.
- Index on `(tenant_id, user_id, created_at)` where `user_id is not null`.
- Index on `(tenant_id, surface, created_at)`.

### agent_tools

Stores read-only dashboard tool metadata for discovery.

Agent tools are internal dashboard features and must not be exposed through public widget APIs.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, nullable |
| `name` | `text` | Not null |
| `description` | `text` | Not null |
| `input_schema` | `jsonb` | Not null, default `{}` |
| `read_only` | `boolean` | Not null, default `true` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `(tenant_id, name)`.
- Index on `(tenant_id, read_only)`.

Relationship notes:

- `tenant_id` may be null for globally available dashboard tools.
- V1/V2 tools must be read-only.

## Chroma Vector Storage Notes

Chroma stores embeddings for rows from `document_chunks`.

Recommended Chroma metadata per vector:

```json
{
  "tenant_id": "uuid",
  "document_id": "uuid",
  "chunk_id": "uuid",
  "chunk_index": 0,
  "source_type": "pdf",
  "visibility": "public",
  "source": "uploaded-file-name.pdf",
  "title": "Return Policy"
}
```

Storage rules:

- Use one collection for V1/V2 unless tenant scale requires separate collections later.
- Every vector must include `tenant_id`.
- Every vector must include `visibility`.
- Protected dashboard retrieval must filter by `tenant_id` and may use internal or public chunks according to permissions.
- Public widget retrieval must filter by `tenant_id` and `visibility = 'public'`.
- The returned `chunk_id` should be verified against PostgreSQL before source display.
- PostgreSQL remains the source of truth for document and chunk metadata.
