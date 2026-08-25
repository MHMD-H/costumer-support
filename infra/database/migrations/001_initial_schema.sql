create extension if not exists pgcrypto;

create table tenants (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    shop_id text,
    shop_domain text,
    widget_public_key text,
    widget_enabled boolean not null default true,
    widget_allowed_origins jsonb not null default '[]'::jsonb,
    widget_settings jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index tenants_shop_id_key
    on tenants (shop_id)
    where shop_id is not null;

create unique index tenants_shop_domain_key
    on tenants (shop_domain)
    where shop_domain is not null;

create unique index tenants_widget_public_key_key
    on tenants (widget_public_key)
    where widget_public_key is not null;

create index tenants_shop_domain_widget_public_key_idx
    on tenants (shop_domain, widget_public_key);

create table users (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    auth_user_id uuid not null unique,
    name text not null,
    email text not null,
    role text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint users_role_check
        check (role in ('store_owner', 'marketing_manager', 'team_member', 'admin')),
    constraint users_tenant_id_email_key unique (tenant_id, email)
);

create index users_tenant_id_role_idx
    on users (tenant_id, role);

create table permissions (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    user_id uuid not null references users (id),
    permission text not null,
    created_at timestamptz not null default now(),
    constraint permissions_tenant_id_user_id_permission_key
        unique (tenant_id, user_id, permission)
);

create index permissions_tenant_id_permission_idx
    on permissions (tenant_id, permission);

create table products (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    external_product_id text,
    name text not null,
    description text,
    category text,
    price numeric(12, 2),
    status text not null,
    public_visible boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint products_price_check
        check (price is null or price >= 0),
    constraint products_status_check
        check (status in ('active', 'inactive', 'archived'))
);

create unique index products_tenant_id_external_product_id_key
    on products (tenant_id, external_product_id)
    where external_product_id is not null;

create index products_tenant_id_status_idx
    on products (tenant_id, status);

create index products_tenant_id_category_idx
    on products (tenant_id, category);

create index products_tenant_id_public_visible_idx
    on products (tenant_id, public_visible);

create table orders (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    user_id uuid references users (id),
    status text not null,
    total_amount numeric(12, 2) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint orders_status_check
        check (status in ('pending', 'paid', 'fulfilled', 'cancelled', 'refunded')),
    constraint orders_total_amount_check
        check (total_amount >= 0)
);

create index orders_tenant_id_status_idx
    on orders (tenant_id, status);

create index orders_tenant_id_user_id_idx
    on orders (tenant_id, user_id);

create index orders_tenant_id_created_at_idx
    on orders (tenant_id, created_at);

create table sales (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    order_id uuid not null references orders (id),
    product_id uuid references products (id),
    amount numeric(12, 2) not null,
    created_at timestamptz not null default now(),
    constraint sales_amount_check
        check (amount >= 0)
);

create index sales_tenant_id_created_at_idx
    on sales (tenant_id, created_at);

create index sales_tenant_id_product_id_idx
    on sales (tenant_id, product_id);

create index sales_tenant_id_order_id_idx
    on sales (tenant_id, order_id);

create table campaigns (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    name text not null,
    channel text not null,
    spend numeric(12, 2) not null,
    revenue numeric(12, 2) not null,
    roas numeric(12, 4) not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint campaigns_spend_check
        check (spend >= 0),
    constraint campaigns_revenue_check
        check (revenue >= 0),
    constraint campaigns_roas_check
        check (roas >= 0)
);

create index campaigns_tenant_id_channel_idx
    on campaigns (tenant_id, channel);

create index campaigns_tenant_id_created_at_idx
    on campaigns (tenant_id, created_at);

create table documents (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    uploaded_by_user_id uuid not null references users (id),
    title text not null,
    type text not null,
    source text not null,
    visibility text not null default 'internal',
    status text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint documents_type_check
        check (type in ('pdf', 'docx', 'txt', 'markdown', 'notion', 'web', 'csv')),
    constraint documents_visibility_check
        check (visibility in ('internal', 'public')),
    constraint documents_status_check
        check (status in ('uploaded', 'processing', 'ready', 'failed'))
);

create index documents_tenant_id_status_idx
    on documents (tenant_id, status);

create index documents_tenant_id_type_idx
    on documents (tenant_id, type);

create index documents_tenant_id_visibility_idx
    on documents (tenant_id, visibility);

create index documents_tenant_id_created_at_idx
    on documents (tenant_id, created_at);

create table document_chunks (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    document_id uuid not null references documents (id),
    chunk_index integer not null,
    content text not null,
    visibility text not null,
    chroma_collection text not null,
    chroma_vector_id text not null unique,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    constraint document_chunks_chunk_index_check
        check (chunk_index >= 0),
    constraint document_chunks_visibility_check
        check (visibility in ('internal', 'public')),
    constraint document_chunks_document_id_chunk_index_key
        unique (document_id, chunk_index)
);

create index document_chunks_tenant_id_document_id_idx
    on document_chunks (tenant_id, document_id);

create index document_chunks_tenant_id_visibility_idx
    on document_chunks (tenant_id, visibility);

create table conversations (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    user_id uuid references users (id),
    surface text not null,
    visitor_id text,
    shop_domain text,
    title text,
    status text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint conversations_surface_check
        check (surface in ('dashboard', 'widget')),
    constraint conversations_status_check
        check (status in ('active', 'archived'))
);

create index conversations_tenant_id_user_id_created_at_idx
    on conversations (tenant_id, user_id, created_at);

create index conversations_tenant_id_surface_created_at_idx
    on conversations (tenant_id, surface, created_at);

create index conversations_tenant_id_visitor_id_idx
    on conversations (tenant_id, visitor_id)
    where visitor_id is not null;

create index conversations_tenant_id_status_idx
    on conversations (tenant_id, status);

create table messages (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    conversation_id uuid not null references conversations (id),
    sender text not null,
    content text not null,
    sources jsonb not null default '[]'::jsonb,
    used_tools jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    constraint messages_sender_check
        check (sender in ('user', 'customer', 'assistant', 'system'))
);

create index messages_tenant_id_conversation_id_created_at_idx
    on messages (tenant_id, conversation_id, created_at);

create table feedback (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references tenants (id),
    user_id uuid references users (id),
    conversation_id uuid not null references conversations (id),
    message_id uuid not null references messages (id),
    surface text not null,
    rating integer not null,
    comment text,
    created_at timestamptz not null default now(),
    constraint feedback_surface_check
        check (surface in ('dashboard', 'widget')),
    constraint feedback_rating_check
        check (rating between 1 and 5)
);

create index feedback_tenant_id_message_id_idx
    on feedback (tenant_id, message_id);

create index feedback_tenant_id_user_id_created_at_idx
    on feedback (tenant_id, user_id, created_at)
    where user_id is not null;

create index feedback_tenant_id_surface_created_at_idx
    on feedback (tenant_id, surface, created_at);

create table agent_tools (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid references tenants (id),
    name text not null,
    description text not null,
    input_schema jsonb not null default '{}'::jsonb,
    read_only boolean not null default true,
    created_at timestamptz not null default now(),
    constraint agent_tools_read_only_check
        check (read_only)
);

create unique index agent_tools_tenant_id_name_key
    on agent_tools (tenant_id, name);

create index agent_tools_tenant_id_read_only_idx
    on agent_tools (tenant_id, read_only);
