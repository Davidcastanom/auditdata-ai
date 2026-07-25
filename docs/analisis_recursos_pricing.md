# ============================================================================
# ANALISIS DE CONSUMO DE RECURSOS Y MODELO DE PRECIOS
# AuditData AI - Futuro SaaS
# ============================================================================
#
# FECHA: 2026-07-24
# VERSION: 1.0
# OBJETIVO: Analizar consumo real por dataset para definir precios futuros
#
# ============================================================================
## RESUMEN EJECUTIVO
# ============================================================================

Cada dataset procesado consume recursos en 5 componentes:

| Componente          | Costo Unitario | Tiempo  | Memoria  |
|---------------------|----------------|---------|----------|
| Diagnostico (28cat) | $0.0000        | ~50ms   | 2-5 MB   |
| IA Groq (Llama 3.1) | $0.0000        | ~1.2s   | minimo   |
| Graficas (4 PNG)    | $0.0000        | ~200ms  | 50-100MB |
| PDF ReportLab       | $0.0000        | ~500ms  | 20-50 MB |
| Supabase (historial)| $0.0001        | inmediato| 800 KB  |
| **TOTAL**           | **~$0.0001**   | **~2s** | **~100MB** |

# ============================================================================
## 1. DESGLOSE POR COMPONENTE
# ============================================================================

### 1.1 MOTOR DE DIAGNOSTICO (data_engine/diagnostic.py)
- Complejidad: O(C x R) donde C=columnas, R=filas
- Checks por columna: 19 funciones de deteccion
- Memoria: 2-5 MB (valores como strings en RAM)
- CPU: ~50ms para 10 columnas x 10,000 filas
- COSTO: $0 (solo CPU, sin llamadas externas)

### 1.2 ADVISOR DE IA (data_engine/ai_advisor.py)
- API: Groq (llama-3.1-8b-instant)
- Llamadas: 1 por columna con problemas
- Tokens por llamada: ~800 input + ~500 output = ~1,300 tokens
- Latencia: ~200ms por llamada
- COSTO: $0 (tier gratuito: 14,400 req/dia)

EJEMPLO:
  Dataset 10 columnas, 6 con problemas
  = 6 llamadas x 1,300 tokens = 7,800 tokens totales
  = 6 x 200ms = 1.2 segundos

### 1.3 GRAFICAS MATPLOTLIB (data_engine/charts.py)
- Graficas generadas: 4 (missing, types, gauge, summary)
- DPI: 150
- Tamano base64: 50-200 KB por grafica
- Memoria pico: 50-100 MB (4 figuras simultaneas)
- CPU: ~200ms total
- COSTO: $0 (solo CPU)

### 1.4 PDF CON REPORTLAB (backend/app/reporting.py)
- Tamano PDF: 100-500 KB
- CPU: ~500ms
- Memoria: 20-50 MB
- COSTO: $0 (solo CPU)

### 1.5 ALMACENAMIENTO SUPABASE (backend/app/auth.py)
- Tamano por sesion: ~800 KB
  - PDF base64: ~300 KB
  - Metadata JSON: ~10 KB
  - CSV limpio: ~500 KB
- Plan gratuito Supabase: 1 GB
- COSTO: $0.0001 por sesion (almacenamiento)

# ============================================================================
## 2. ESCALADO POR TAMANO DE DATASET
# ============================================================================

### Dataset pequeno (1-5 columnas, <1,000 filas)
- Diagnostico: ~10ms
- IA: 1-3 llamadas (~600ms)
- Graficas: ~100ms
- PDF: ~200ms
- Almacenamiento: ~300 KB
- **Tiempo total: ~1 segundo**
- **Costo: ~$0.00005**

### Dataset mediano (6-15 columnas, 1,000-50,000 filas)
- Diagnostico: ~50ms
- IA: 4-10 llamadas (~1.5s)
- Graficas: ~200ms
- PDF: ~500ms
- Almacenamiento: ~800 KB
- **Tiempo total: ~2.5 segundos**
- **Costo: ~$0.0001**

### Dataset grande (16-50 columnas, 50,000-500,000 filas)
- Diagnostico: ~500ms
- IA: 10-30 llamadas (~5s)
- Graficas: ~500ms
- PDF: ~2s
- Almacenamiento: ~2 MB
- **Tiempo total: ~8 segundos**
- **Costo: ~$0.0003**

### Dataset muy grande (50+ columnas, 500,000+ filas)
- Diagnostico: ~5s
- IA: 30+ llamadas (~10s)
- Graficas: ~1s
- PDF: ~5s
- Almacenamiento: ~5 MB
- **Tiempo total: ~20 segundos**
- **Costo: ~$0.001**

# ============================================================================
## 3. MODELO DE PRECIOS PROPUESTO
# ============================================================================

### PLAN GRATUITO
- 10 analisis/mes
- 1 dataset por analisis (max 5 MB)
- 10 columnas maximo
- PDF basico (sin graficas)
- Sin historial en la nube
- COSTO OPERATIVO: ~$0.001/mes

### PLAN PROFESIONAL ($19/mes)
- 100 analisis/mes
- 5 datasets por analisis (max 10 MB)
- 50 columnas maximo
- PDF completo con graficas
- Historial 30 dias en Supabase
- IA con Groq (recomendaciones)
- Nube de Validacion
- COSTO OPERATIVO: ~$0.01/mes
- MARGEN: 99.9%

### PLAN EMPRESARIAL ($49/mes)
- Analisis ilimitados
- Sin limite de columnas
- PDF personalizado con branding
- Historial 90 dias
- IA con Groq + Gemini (opcional)
- API access
- Soporte prioritario
- COSTO OPERATIVO: ~$0.05/mes
- MARGEN: 99.9%

### PLAN API ($0.002/analisis)
- Para integraciones
- JSON response (sin PDF)
- Rate limit: 100 req/min
- COSTO OPERATIVO: ~$0.0001/analisis
- MARGEN: 95%

# ============================================================================
## 4. COSTOS DE INFRAESTRUCTURA (RENDER)
# ============================================================================

### Servicio actual: Render.com
- Plan: Free tier (actualmente)
- RAM: 512 MB
- CPU: Shared
- STORAGE: 0 GB (temp)

### Plan Starter ($7/mes)
- RAM: 512 MB
- CPU: Shared
- Alcanza para: ~100 usuarios activos

### Plan Standard ($25/mes)
- RAM: 2 GB
- CPU: 1 GB
- Alcanza para: ~500 usuarios activos

### Plan Pro ($85/mes)
- RAM: 4 GB
- CPU: 2 GB
- Alcanza para: ~2,000 usuarios activos

# ============================================================================
## 5. COSTOS DE SUPABASE
# ============================================================================

### Plan Gratis
- 1 GB almacenamiento
- 50,000 filas
- 500 MB transferencia
- Alcanza para: ~500 sesiones/mes

### Plan Pro ($25/mes)
- 100 GB almacenamiento
- 10,000,000 filas
- 250 GB transferencia
- Alcanza para: ~50,000 sesiones/mes

# ============================================================================
## 6. PROYECCION DE INGRESOS (12 MESES)
# ============================================================================

### Mes 1-3 (Lanzamiento)
- Usuarios gratuitos: 100
- Usuarios pagos: 5
- Ingresos: $95/mes
- Costos: $32/mes (Render + Supabase)
- Beneficio: $63/mes

### Mes 4-6 (Crecimiento)
- Usuarios gratuitos: 500
- Usuarios pagos: 25
- Ingresos: $475/mes
- Costos: $50/mes
- Beneficio: $425/mes

### Mes 7-12 (Madurez)
- Usuarios gratuitos: 2,000
- Usuarios pagos: 100
- Ingresos: $1,900/mes
- Costos: $110/mes
- Beneficio: $1,790/mes

# ============================================================================
## 7. METRICAS CLAVE (KPIs)
# ============================================================================

| Metrica                    | Valor Actual | Objetivo 6 meses |
|----------------------------|--------------|------------------|
| Costo por analisis         | $0.0001      | < $0.001         |
| Tiempo promedio            | 2.5s         | < 3s             |
| Tasa conversion gratis→pago| N/A          | 5%               |
| Churn mensual              | N/A          | < 5%             |
| LTV (Lifetime Value)       | N/A          | > $200           |
| CAC (Customer Acq Cost)    | N/A          | < $50            |

# ============================================================================
## 8. RECOMENDACIONES
# ============================================================================

1. **Empezar con plan gratuito generoso** - Genera base de usuarios
2. **Monetizar funcionalidad avanzada** - PDF, historial, IA
3. **Mantener Groq como proveedor IA** - Es gratis y rapido
4. **Considerar Gemini como upgrade** - Para usuarios enterprise
5. **Usar Render free tier** - Mientras no hay muchos usuarios
6. **Supabase gratis** - Alcanza para los primeros 500 usuarios

# ============================================================================
## 9. RIESGOS
# ============================================================================

| Riesgo                         | Probabilidad | Impacto | Mitigacion |
|--------------------------------|--------------|---------|------------|
| Groq cambia politica gratuita  | Baja         | Alto    | Respaldo con Gemini |
| Render limita free tier        | Media        | Medio   | Migrar a Railway/VPS |
| Supabase excede limites        | Baja         | Medio   | Upgradear a Pro |
| Demasiados usuarios gratis     | Media        | Bajo    | Limitar features |

# ============================================================================
## CONCLUSION
# ============================================================================

El costo operativo real por dataset es extremadamente bajo (~$0.0001).
Esto permite márgenes del 99%+ en planes de suscripcion.

El modelo de negocio mas viable es:
- GRATUITO para adquisicion
- PROFESIONAL ($19/mes) para monetizacion principal
- API ($0.002/analisis) para integraciones

El break-even se alcanza con solo 2 usuarios pagando el plan profesional.
