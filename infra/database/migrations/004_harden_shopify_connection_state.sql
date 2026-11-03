delete from public.shopify_oauth_states;

alter table public.shopify_oauth_states
    add column shop_domain text not null;

alter table public.shopify_connections
    drop column access_token_encrypted;
