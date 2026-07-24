-- AuditData AI - Supabase Schema
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard/project/_/sql)

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users table (auto-created by Supabase Auth, but we add extra fields)
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  full_name text,
  email text,
  avatar_url text,
  created_at timestamp with time zone default now() not null,
  updated_at timestamp with time zone default now() not null
);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, full_name, email, avatar_url)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name', ''),
    coalesce(new.raw_user_meta_data ->> 'email', ''),
    coalesce(new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture', '')
  );
  return new;
end;
$$ language plpgsql security definer;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Datasets table
create table if not exists public.datasets (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  filename text not null,
  content_base64 text not null,
  row_count integer default 0,
  column_count integer default 0,
  created_at timestamp with time zone default now() not null
);

-- Analyses table
create table if not exists public.analyses (
  id uuid default uuid_generate_v4() primary key,
  dataset_id uuid references public.datasets(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  analysis_json jsonb not null,
  row_meaning text default '',
  analysis_objective text default '',
  created_at timestamp with time zone default now() not null
);

-- Cleaning sessions table
create table if not exists public.cleaning_sessions (
  id uuid default uuid_generate_v4() primary key,
  dataset_id uuid references public.datasets(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  actions_json jsonb not null default '[]'::jsonb,
  before_json jsonb,
  after_json jsonb,
  changelog_json jsonb default '[]'::jsonb,
  analyst text default '',
  version text default 'v1.0',
  created_at timestamp with time zone default now() not null
);

-- Row Level Security (RLS) - users can only see their own data
alter table public.profiles enable row level security;
alter table public.datasets enable row level security;
alter table public.analyses enable row level security;
alter table public.cleaning_sessions enable row level security;

-- Profiles: users can read/update their own profile
create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- Datasets: users can CRUD their own datasets
create policy "Users can view own datasets"
  on public.datasets for select
  using (auth.uid() = user_id);

create policy "Users can insert own datasets"
  on public.datasets for insert
  with check (auth.uid() = user_id);

create policy "Users can update own datasets"
  on public.datasets for update
  using (auth.uid() = user_id);

create policy "Users can delete own datasets"
  on public.datasets for delete
  using (auth.uid() = user_id);

-- Analyses: users can CRUD their own analyses
create policy "Users can view own analyses"
  on public.analyses for select
  using (auth.uid() = user_id);

create policy "Users can insert own analyses"
  on public.analyses for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own analyses"
  on public.analyses for delete
  using (auth.uid() = user_id);

-- Cleaning sessions: users can CRUD their own sessions
create policy "Users can view own cleaning sessions"
  on public.cleaning_sessions for select
  using (auth.uid() = user_id);

create policy "Users can insert own cleaning sessions"
  on public.cleaning_sessions for insert
  with check (auth.uid() = user_id);

create policy "Users can update own cleaning sessions"
  on public.cleaning_sessions for update
  using (auth.uid() = user_id);

create policy "Users can delete own cleaning sessions"
  on public.cleaning_sessions for delete
  using (auth.uid() = user_id);

-- Indexes for performance
create index if not exists datasets_user_id_idx on public.datasets(user_id);
create index if not exists analyses_dataset_id_idx on public.analyses(dataset_id);
create index if not exists analyses_user_id_idx on public.analyses(user_id);
create index if not exists cleaning_sessions_dataset_id_idx on public.cleaning_sessions(dataset_id);
create index if not exists cleaning_sessions_user_id_idx on public.cleaning_sessions(user_id);
