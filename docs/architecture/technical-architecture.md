# Arquitectura Tecnica - AuditData AI

## Vision

La arquitectura separa experiencia visual, API y motor de datos para que el proyecto pueda evolucionar sin reconstruirse.

## Capas

### Frontend

Responsable de:

- cargar archivos,
- presentar resultados,
- solicitar reportes,
- aplicar el Design System.

No debe contener credenciales ni logica profunda de calidad de datos.

### Backend

Responsable de:

- servir la interfaz local,
- recibir archivos codificados,
- llamar al motor Python,
- generar reportes,
- actuar como punto seguro para futuras integraciones de IA.

### Data Engine

Responsable de:

- leer datasets,
- perfilar columnas,
- detectar problemas,
- calcular scores,
- generar recomendaciones reutilizables.

### Reporting

Responsable de:

- producir salidas ejecutivas,
- mantener formato profesional,
- reutilizar la paleta del proyecto.

## Futuro con IA

La IA debe vivir detras del backend. Su rol recomendado es:

- sugerir reglas de negocio,
- redactar narrativa,
- agrupar errores tipograficos,
- explicar riesgos.

El motor Python conserva la responsabilidad de calcular datos reales.

