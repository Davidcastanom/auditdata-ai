# Documentación recomendada antes de seguir desarrollando — AuditData AI

**Fecha de creación:** 2026-08-07 · **Autor:** AuditData AI · **Estado:** REFERENCIA / CHECKLIST PENDIENTE

> Propósito: tener registrada la documentación que conviene cerrar antes de tirar la siguiente línea de
> código o de lanzar el producto. Ya existe: aviso de privacidad (`/privacidad`, RGPD / Ley 1581/2012 /
> CCPA-CPRA), Términos y Condiciones (`/terminos`), modal de consentimiento (v2.1), README y plan de
> mejora del copiloto IA. Esta lista cubre lo que falta y está priorizada por riesgo/valor.

## Alta prioridad — riesgo legal y de datos

### 1. ROPA — Registro de actividades de tratamiento
- **Qué:** matriz de "qué dato se procesa, para qué finalidad, con qué base legal, por cuánto tiempo, a quién se transfiere".
- **Por qué:** es lo que exige la Superintendencia de Industria y Comercio (Ley 1581/2012) y el RGPD; es el respaldo operativo del aviso de privacidad.
- **Contenido mínimo:** finalidad (diagnóstico, limpieza, IA, historial, telemetría, OAuth), categorías de datos, base legal, plazos de conservación, destinatarios (Groq, Supabase, Google), medidas de seguridad.
- **Estado:** PENDIENTE

### 2. Política de retención y borrado
- **Qué:** plazos concretos de conservación y el procedimiento operativo de borrado (a petición y automático).
- **Por qué:** sin esto, la promesa del aviso de "puedes borrar tu historial en cualquier momento" no es operable.
- **Contenido mínimo:** plazo de retención del historial en Supabase, qué se borra exactamente (datasets, analyses, cleaning_sessions, user_consents), cómo se ejecuta el borrado, tiempos de respuesta (15 días hábiles Colombia / 30 días RGPD).
- **Estado:** PENDIENTE

### 3. DPIA — Evaluación de impacto de protección de datos
- **Qué:** análisis documentado de los riesgos de tratar datos sensibles y de enviarlos a un tercero (Groq).
- **Por qué:** el flujo de IA envía columnas, preguntas y valores de ejemplo a un proveedor externo; la DPIA documenta el riesgo, las mitigaciones (anonimización, autorización expresa, avisos) y decide si el tratamiento es proporcional.
- **Contenido mínimo:** contexto del tratamiento, riesgos (intercepción, subprocesamiento, jurisdicción del proveedor), mitigaciones (existentes y propuestas, incluida la anonimización de valores antes de Groq), veredicto.
- **Estado:** PENDIENTE

### 4. DPA de proveedores (revisión y archivo)
- **Qué:** leer, archivar y entender los contratos de procesamiento de datos (DPA) de Supabase, Groq y Google OAuth.
- **Por qué:** hay que confirmar si el proveedor puede subprocesar, bajo qué jurisdicción y qué garantías ofrece. Es la evidencia de que el responsable hizo la diligencia debida.
- **Estado:** PENDIENTE

## Alta prioridad — técnica (antes de codear)

### 5. Spec de requerimientos (funcionales y no funcionales)
- **Qué:** documento de qué debe hacer el sistema y con qué criterios de aceptación.
- **Por qué:** evita que requisitos tipo "el copiloto debe ser honesto" dependan de una conversación; cada requerimiento debe tener un test de aceptación.
- **Contenido mínimo:** por feature → descripción, criterios de aceptación, casos borde. NFR → rendimiento (latencia objetivo del chat), privacidad, disponibilidad, costos de tokens.
- **Estado:** PENDIENTE

### 6. ADRs — Architecture Decision Records
- **Qué:** decisiones de arquitectura tomadas y su motivo, en archivos cortos por decisión.
- **Por qué:** FastAPI, Groq free (6000 TPM, llama-3.1-8b-instant), cache en memoria por hash, supresión del 413, autorización de datos sensibles, anonimización pendiente: registrar el porqué evita revertirlas por error.
- **Contenido mínimo:** contexto, decisión, alternativas consideradas, consecuencias.
- **Estado:** PENDIENTE

### 7. AGENTS.md / convenciones del repositorio
- **Qué:** fichero en la raíz con los comandos y reglas que un agente (opencode) o un nuevo desarrollador debe conocer.
- **Por qué:** pruebas (272 Python + 44 E2E), lint (`ruff check --select F,E9`), estructura del repo, convenciones de commit y de tests (test-first). Reduce el riesgo de romper la suite.
- **Estado:** PENDIENTE

## Media prioridad — operativa

### 8. Playbook de incidentes y brechas de datos
- **Qué:** qué hacer si hay una fuga de datos: detección, contención, notificación.
- **Por qué:** RGPD exige notificar en 72 h; Colombia exige informar sin demora. Tener la plantilla y el listado de contactos ahorra tiempo crítico.
- **Contenido mínimo:** qué se considera brecha, responsables, pasos, plantilla de notificación (autoridad + titulares), registro del incidente.
- **Estado:** PENDIENTE

### 9. Política de cookies y almacenamiento local
- **Qué:** documentar el uso de localStorage, OAuth y (si algún día se añaden) cookies de seguimiento.
- **Por qué:** en mercados UE es obligatorio informar de las cookies; hoy la app usa localStorage (consentimiento, historial de sesión) y OAuth de Google, que conviene declarar.
- **Contenido mínimo:** qué se almacena, para qué, cómo se limpia (cierre de sesión), banner/política si aplica.
- **Estado:** PENDIENTE

## Resumen

| # | Documento | Prioridad | Estado |
|---|-----------|-----------|--------|
| 1 | ROPA — Registro de actividades de tratamiento | Alta | PENDIENTE |
| 2 | Política de retención y borrado | Alta | PENDIENTE |
| 3 | DPIA — Evaluación de impacto | Alta | PENDIENTE |
| 4 | DPA de proveedores (revisión) | Alta | PENDIENTE |
| 5 | Spec de requerimientos | Alta | PENDIENTE |
| 6 | ADRs de arquitectura | Alta | PENDIENTE |
| 7 | AGENTS.md (convenciones del repo) | Alta | PENDIENTE |
| 8 | Playbook de incidentes / brechas | Media | PENDIENTE |
| 9 | Política de cookies / almacenamiento local | Media | PENDIENTE |

**Siguiente paso sugerido:** generar primero los documentos 1, 2 y 7 (máximo valor por esfuerzo: ROPA, retención y AGENTS.md).
