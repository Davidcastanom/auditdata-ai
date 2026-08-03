-- Migración 004: permitir que cada usuario ELIMINE su propio historial en la nube.
--
-- Aplica sobre las tablas datasets, analyses y cleaning_sessions (creadas
-- manualmente en Supabase). El borrado se hace desde el botón "X" del panel
-- de historial. Nunca permite borrar datos de otros usuarios.
--
-- Requiere que ROW LEVEL SECURITY ya esté habilitado en esas tablas (como al
-- crear las políticas SELECT/INSERT para guardar el historial).
--
-- Cómo aplicar:
-- 1. Abre Supabase → SQL Editor
-- 2. Pega y ejecuta este script

-- datasets
drop policy if exists "datasets_delete_own" on public.datasets;
create policy "datasets_delete_own"
  on public.datasets for delete
  using (auth.uid() = user_id);

-- analyses (referencian a datasets del mismo usuario)
drop policy if exists "analyses_delete_own" on public.analyses;
create policy "analyses_delete_own"
  on public.analyses for delete
  using (auth.uid() = user_id);

-- cleaning_sessions
drop policy if exists "cleaning_sessions_delete_own" on public.cleaning_sessions;
create policy "cleaning_sessions_delete_own"
  on public.cleaning_sessions for delete
  using (auth.uid() = user_id);
