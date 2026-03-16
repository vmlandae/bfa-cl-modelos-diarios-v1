# F26: Sistema de Reportes Email Multi-Tipo

> **Tamaño:** M (~3d) · **Asignado:** @vlandaetat · **Sprint:** S2-2026
> **Rama:** `feature/email-report`
> **Fecha inicio:** 2026-03-12

---

## Contexto

El sistema actual (`core/email_report.py`) soporta un único tipo de reporte:
amortización de primera vuelta comparando dos fechas de proceso.

Se necesita evolucionar a un sistema multi-tipo que soporte:

1. **Reporte primera vuelta** — ya implementado (amortización por moneda/producto)
2. **Reporte segunda vuelta** — mismo formato, tablas de vuelta 2
3. **Reporte chequeo de interfaces** — sumas de amortización, interés y conteo
   de registros agrupados por SISTEMA y MONEDA_ORIGEN a partir de los archivos
   PML GCP y CMR

Además, se requiere integración con el orquestador (envío post-ejecución) y,
a futuro, con el dashboard Streamlit (botón de envío manual).

---

## Criterio de UX: fechas reales, nunca t/t-1

En toda comunicación visible al usuario (emails, tablas, gráficos, logs) se
deben mostrar las **fechas de proceso reales** (ej: "2026-03-10 vs 2026-03-07")
en vez de etiquetas genéricas como "t" o "t-1".  Internamente las variables
pueden usar `t` / `t1`, pero los labels visibles siempre llevan la fecha.

---

## Fases de implementación

### Fase 1 — Reestructuración YAML + refactor base ✅→🔄

**Objetivo:** Config multi-tipo + infraestructura compartida.

**Cambios:**
- Reestructurar `email_report:` en YAML: config compartida (enabled, destinatarios,
  modo) + sub-secciones por tipo con `asunto_template` propio.
- Refactorizar `email_report.py`: parametrizar por `tipo_reporte`, extraer
  constantes `TABLAS_SEGUNDA_VUELTA`, unificar lógica de envío.

**Archivos:**
- `config/config_rutas_ext_y_archivos.yaml`
- `core/email_report.py`

### Fase 2 — Reporte segunda vuelta

**Objetivo:** Generar reporte de amortización para modelos de vuelta 2.

**Tablas BQ segunda vuelta (hist):**
- `report_mr_prepago_cmr_hist`
- `report_ml_nmd_hist`
- `report_ml_lc_hist`
- `report_ml_inversiones_hist`

**Cambios:**
- Agregar `TABLAS_SEGUNDA_VUELTA` y `CODIGO_PRODUCTOS_V2` en email_report.py
- Reutilizar el pipeline existente (comparación, charts, Excel, HTML, envío)

### Fase 3 — Actualización run_diario.bat

**Objetivo:** Menú post-ejecución que envíe el reporte correspondiente a la
vuelta ejecutada.

**Lógica:**
- Si ejecutó solo primera vuelta → ofrecer reporte primera vuelta
- Si ejecutó solo segunda vuelta → ofrecer reporte segunda vuelta
- Si ejecutó ambas → ofrecer ambos reportes (o uno consolidado)

### Fase 4 — Integración con orquestador

**Objetivo:** Hook post-ejecución para envío de email.

**Cambios:**
- Nuevo método `_post_ejecucion_email()` en `OrquestadorModelos`
- Lee config YAML para decidir si auto-enviar
- Selecciona tipo de reporte según vueltas ejecutadas

### Fase 5 — Reporte chequeo de interfaces (pendiente detalle)

**Objetivo:** Validar archivos PML GCP y CMR con sumas de control.

**Contenido del reporte:**
- Sumas de amortización e interés por SISTEMA y MONEDA_ORIGEN (GCP)
- Conteo de registros por SISTEMA y MONEDA_ORIGEN
- Comparación entre archivos GCP y CMR

> ⚠️ Requiere más detalle del usuario sobre estructura de archivos y campos.

### Fase 6 — Dashboard email button (diferido)

**Objetivo:** Botón en Streamlit dashboard para enviar reporte del día.

> Diferido hasta que `feature/email-report` y `feature/dashboard-quick-wins`
> converjan en `main`.

### Fase 7 — Auto-send inteligente (solo planificación)

**Objetivo:** Envío automático solo si las diferencias entre fechas son
pequeñas/consistentes con patrones históricos.

> Solo planificación. Requiere definir umbrales y baseline histórica.

---

## Criterios de aceptación

- [ ] Config YAML soporta 3 tipos de reporte con asunto_template independiente
- [ ] `generar_y_enviar_reporte()` acepta parámetro `tipo_reporte`
- [ ] Reporte segunda vuelta genera comparación, charts, Excel y email
- [ ] `run_diario.bat` ofrece reporte correcto según vuelta ejecutada
- [ ] Orquestador puede enviar email como hook post-ejecución
- [ ] Todas las etiquetas visibles usan fechas reales, nunca "t" ni "t-1"

---

## Dependencias

- `core/email_report.py` (primera vuelta ya funcional)
- BigQuery tables históricas (primera y segunda vuelta)
- Outlook COM vía pywin32
- kaleido para generación de charts PNG
