alter table public.users
    add column is_active boolean not null default true,
    add constraint users_auth_user_id_fkey
        foreign key (auth_user_id) references auth.users (id);
