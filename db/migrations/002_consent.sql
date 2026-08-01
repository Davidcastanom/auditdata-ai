"""Migración 002: tabla de consentimiento de tratamiento de datos.

Guarda la aceptación del usuario (huella legal de que leyó y aceptó el
disclaimer ANTES de que su historial se guarde en la nube).

Cómo aplicar (una sola vez):
1. Abre Supabase → SQL Editor
2. Pega y ejecuta este script
"""

-- ============================================================
-- TABLA DE CONSENTIMIENTO
-- ============================================================
create table if not exists public.user_consents (
  user_id uuid primary key references auth.users(id) on delete cascade,
  consent_version text not null default '1.0',
  accepted_at timestamptz not null default now()
);

-- ============================================================
-- ROW LEVEL SECURITY: cada usuario solo ve/escribe SU consentimiento
-- ============================================================
alter table public.user_consents enable row level security;

drop policy if exists "user_consents_insert_own" on public.user_consents;
create policy "user_consents_insert_own"
  on public.user_consents for insert
  with check (auth.uid() = user_id);

drop policy if exists "user_consents_select_own" on public.user_consents;
create policy "user_consents_select_own"
  on public.user_consents for select
  using (auth.uid() = user_id);

drop policy if exists "user_consents_update_own" on public.user_consents;
create policy "user_consents_update_own"
  on public.user_consents for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
