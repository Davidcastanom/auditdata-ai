# AuditData AI — automatización de desarrollo
# Uso: make test | make lint | make migrate | make send-errors | make run

PYTHON ?= python
DEPLOY_URL ?= https://auditdata-ai-1.onrender.com

.PHONY: test lint migrate send-errors run

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check data_engine/ backend/ tests/

# Aplica el esquema de métricas y consentimiento en Supabase (SQL Editor o `supabase db push`)
migrate:
	@echo "Abre db/migrations/001_metrics.sql y 002_consent.sql en el SQL Editor de Supabase (o usa: supabase db push)"
	@echo "Tablas: usage_events, error_logs, user_consents | Vistas: v_daily_metrics, v_session_stats, v_error_summary"

# Dispara el envío de errores por email vía el endpoint admin → webhook Make.com
send-errors:
	@test -n "$(ADMIN_TOKEN)" || (echo "Define ADMIN_TOKEN en tu entorno"; exit 1)
	curl -s -X POST "$(DEPLOY_URL)/api/admin/errors/send" -H "Authorization: Bearer $(ADMIN_TOKEN)"

run:
	uvicorn backend.app.main:app --reload --port 8000
