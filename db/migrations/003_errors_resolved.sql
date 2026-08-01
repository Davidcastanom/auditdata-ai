-- Migración 003: permitir marcar errores como resueltos desde el panel admin.
--
-- Cómo aplicar:
-- 1. Abre Supabase → SQL Editor
-- 2. Pega y ejecuta este script
-- 3. (Opcional) después puedes hacer commit de la migración al repo

alter table public.error_logs
  add column if not exists resolved_at timestamptz;

create index if not exists idx_error_logs_resolved_at
  on public.error_logs (resolved_at);
