# V1/V2 Database Schema

## Scope

This schema supports V1 and V2 only:

- Users and tenant isolation.
- Products, orders, sales, and campaigns.
- Document metadata and chunk metadata.
- Conversations, messages, and feedback.
- Read-only agent tool metadata.

PostgreSQL stores structured data and metadata. Chroma stores vector embeddings for document chunks.

## PostgreSQL Conventions

- Primary keys use `uuid`.
- Tenant-owned tables include `tenant_id`.
- Timestamps use `timestamptz`.
- Money values use `numeric(12, 2)`.
- JSON metadata uses `jsonb`.
- All tenant-scoped queries must filter by `tenant_id`.

## Tables

### tenants

Stores businesses using the platform.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `name` | `text` | Not null |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.

Relationship notes:

- A tenant owns users, products, orders, sales, campaigns, documents, conversations, feedback, and agent metadata.

### users

Stores application users mapped to Supabase Auth users.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `auth_user_id` | `uuid` | Unique, not null |
| `name` | `text` | Not null |
| `email` | `text` | Not null |
| `role` | `text` | Not null, check in `customer`, `store_owner`, `marketing_manager`, `team_member`, `admin` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `auth_user_id`.
- Unique index on `(tenant_id, email)`.
- Index on `(tenant_id, role)`.

Relationship notes:

- Customers can own orders and conversations.
- Store owners, marketing managers, team members, and admins access tenant resources according to permissions.

### permissions

Stores optional fine-grained tenant permissions for V1/V2.

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

- RBAC gives broad access.
- This table supports simple ACL checks without introducing a complex policy engine.

### products

Stores product data.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `name` | `text` | Not null |
| `description` | `text` | Nullable |
| `category` | `text` | Nullable |
| `status` | `text` | Not null, check in `active`, `inactive`, `archived` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, status)`.
- Index on `(tenant_id, category)`.
- Search index may be added later for product name and description.

### orders

Stores order headers.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, not null |
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

### sales

Stores sales records used for simple metrics.

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

Stores simple marketing campaign metrics.

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
| `type` | `text` | Not null, check in `pdf`, `docx`, `txt` |
| `source` | `text` | Not null |
| `status` | `text` | Not null, check in `uploaded`, `processing`, `ready`, `failed` |
| `metadata` | `jsonb` | Not null, default `{}` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, status)`.
- Index on `(tenant_id, type)`.
- Index on `(tenant_id, created_at)`.

Relationship notes:

- PostgreSQL stores document ownership and metadata.
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
| `chroma_collection` | `text` | Not null |
| `chroma_vector_id` | `text` | Unique, not null |
| `metadata` | `jsonb` | Not null, default `{}` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Unique index on `(document_id, chunk_index)`.
- Unique index on `chroma_vector_id`.
- Index on `(tenant_id, document_id)`.

Relationship notes:

- Chroma stores the embedding vector.
- PostgreSQL stores the tenant, document relationship, chunk text, and source metadata.
- Retrieval must filter by tenant metadata in Chroma and verify returned chunk IDs against PostgreSQL tenant ownership.

### conversations

Stores chat conversation metadata.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, not null |
| `title` | `text` | Nullable |
| `status` | `text` | Not null, check in `active`, `archived` |
| `created_at` | `timestamptz` | Not null |
| `updated_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, user_id, created_at)`.
- Index on `(tenant_id, status)`.

### messages

Stores user and assistant messages.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `conversation_id` | `uuid` | Foreign key to `conversations.id`, not null |
| `sender` | `text` | Not null, check in `user`, `assistant`, `system` |
| `content` | `text` | Not null |
| `sources` | `jsonb` | Not null, default `[]` |
| `used_tools` | `jsonb` | Not null, default `[]` |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, conversation_id, created_at)`.

Relationship notes:

- `sources` stores source references returned to the user.
- `used_tools` stores read-only tool names used by the Agent.

### feedback

Stores feedback on assistant messages.

| Column | Type | Constraints |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | Foreign key to `tenants.id`, not null |
| `user_id` | `uuid` | Foreign key to `users.id`, not null |
| `conversation_id` | `uuid` | Foreign key to `conversations.id`, not null |
| `message_id` | `uuid` | Foreign key to `messages.id`, not null |
| `rating` | `integer` | Not null, check `rating between 1 and 5` |
| `comment` | `text` | Nullable |
| `created_at` | `timestamptz` | Not null |

Indexes:

- Primary key on `id`.
- Index on `(tenant_id, message_id)`.
- Index on `(tenant_id, user_id, created_at)`.

### agent_tools

Stores read-only tool metadata for discovery.

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

- `tenant_id` may be null for globally available tools.
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
  "document_type": "pdf",
  "source": "uploaded-file-name.pdf",
  "title": "Return Policy"
}
```

Storage rules:

- Use one collection for V1/V2 unless tenant scale requires separate collections later.
- Every vector must include `tenant_id`.
- Retrieval must filter by `tenant_id`.
- The returned `chunk_id` should be verified against PostgreSQL before source display.
- PostgreSQL remains the source of truth for document and chunk metadata.
