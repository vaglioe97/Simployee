-- Run this in the Supabase SQL Editor (supabase.com → your project → SQL Editor)

create table users (
    id bigserial primary key,
    username text unique not null,
    password text not null,
    full_name text not null,
    created_at timestamptz default now()
);

create table user_progress (
    id bigserial primary key,
    user_id bigint not null references users(id),
    job_path_id text not null,
    current_week integer default 1,
    started_at timestamptz default now()
);

create table tasks (
    id bigserial primary key,
    user_id bigint not null references users(id),
    week integer not null,
    title text not null,
    description text not null,
    deliverable text not null,
    status text default 'pending',
    submission text,
    feedback text,
    created_at timestamptz default now()
);

-- Disable Row Level Security so the service_role key can read/write freely.
-- This is safe because the key is stored server-side in secrets.toml and
-- is never exposed to the browser.
alter table users disable row level security;
alter table user_progress disable row level security;
alter table tasks disable row level security;
