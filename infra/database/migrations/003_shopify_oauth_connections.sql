alter table public.users alter column tenant_id drop not null;

create table public.shopify_oauth_states (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users (id),
    state_hash text not null unique,
    expires_at timestamptz not null,
    consumed_at timestamptz,
    created_at timestamptz not null default now()
);

create index shopify_oauth_states_expires_at_idx
    on public.shopify_oauth_states (expires_at);

create table public.shopify_connections (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null unique references public.tenants (id),
    shop_id text not null unique,
    shop_domain text not null unique,
    status text not null default 'active' check (status = 'active'),
    access_token_encrypted text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
