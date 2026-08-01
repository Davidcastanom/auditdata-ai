"""Migración 001: tablas y vistas de métricas anónimas de uso.

POLÍTICA DE SEGURIDAD:
- Solo se guardan métricas anónimas (hash del cliente, endpoint, status, tiempo).
- NUNCA contenido de CSVs, nombres de columnas, textos de chat ni emails.

Cómo aplicar (una sola vez):
1. Abre Supabase → SQL Editor
2. Pega y ejecuta este script
3. (Opcional) crea índices adicionales según tu volumen
"""

-- ============================================================
-- EXTENSIONES
-- ============================================================
create extension if not exists "pgcrypto";  -- para gen_random_uuid()

-- ============================================================
-- TABLAS
-- ============================================================

-- Un evento por cada llamada a /api/*
create table if not exists public.usage_events (
  id uuid primary key default gen_random_uuid(),
  client_hash text not null default '',
  session_id text not null default '',
  endpoint text not null,
  method text not null default 'GET',
  status_code int not null default 200,
  duration_ms numeric not null default 0,
  created_at timestamptz not null default now()
);

-- Solo errores (status >= 400): tipo + endpoint, nunca el detalle
create table if not exists public.error_logs (
  id uuid primary key default gen_random_uuid(),
  client_hash text not null default '',
  endpoint text not null,
  status_code int not null,
  error_type text not null default '',
  created_at timestamptz not null default now()
);

-- ============================================================
-- ÍNDICES
-- ============================================================
create index if not exists idx_usage_events_created_at
  on public.usage_events (created_at);
create index if not exists idx_usage_events_client_hash
  on public.usage_events (client_hash);
create index if not exists idx_usage_events_endpoint
  on public.usage_events (endpoint);
create index if not exists idx_error_logs_created_at
  on public.error_logs (created_at);

-- ============================================================
-- VISTAS PARA EL PANEL ADMIN
-- ============================================================

-- Actividad diaria: usuarios activos, peticiones, tiempos, errores
create or replace view public.v_daily_metrics as
select
  date(created_at) as day,
  count(distinct client_hash) as active_users,
  count(*) as requests,
  round(avg(duration_ms)) as avg_duration_ms,
  round(avg(duration_ms) filter (where status_code < 400)) as avg_ok_duration_ms,
  count(*) filter (where status_code >= 400) as errors
from public.usage_events
group by date(created_at)
order by day desc;

-- Duración de cada sesión (cronómetro): de la primera a la última petición
create or replace view public.v_session_stats as
select
  session_id,
  client_hash,
  min(created_at) as started_at,
  max(created_at) as ended_at,
  round(extract(epoch from (max(created_at) - min(created_at)))) as duration_seconds
from public.usage_events
where session_id <> ''
group by session_id, client_hash
order by started_at desc;

-- Resumen de errores por endpoint (dónde falla el proyecto)
create or replace view public.v_error_summary as
select
  endpoint,
  status_code,
  count(*) as count,
  max(created_at) as last_seen
from public.error_logs
group by endpoint, status_code
order by count desc;

-- ============================================================
-- (Opcional) RETENCIÓN: borra métricas mayores a 12 meses
-- ============================================================
-- delete from public.usage_events
--   where created_at < now() - interval '12 months';
-- delete from public.error_logs
--   where created_at < now() - interval '12 months';
