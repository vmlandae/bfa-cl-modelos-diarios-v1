# Hallazgos: dashboard, email_report, catálogo de modelos

> **Fecha:** 2026-05-13
> **Origen:** Diagnóstico exhaustivo previo al sprint S6-2026 (`Controles & Cobertura Dashboard`).

Este documento consolida lo encontrado en código antes de planificar las features F28-F32. Es la **versión auditable** del diagnóstico: cada gap se cita con `file_path:line`.

---

## 1. Cobertura de modelos en dashboard, email y orquestador

| Modelo | Orquestador | Comparativa (dashboard) | Email V1/V2 | Benchmark (theme.py) | Tabla BQ |
|---|---|---|---|---|---|
| `mr_prepago_consumo` | ✓ | ✓ | ✓ V1 | ✓ | `report_mr_prepago_consumo_dly/_hist` |
| `mr_prepago_hipotecario` | ✓ | ✓ | ✓ V1 | ✓ | `report_mr_prepago_hipotecario_dly/_hist` |
| `mr_prepago_cmr` | ✓ | ✓ | ✓ V2 | ✓ | `report_mr_prepago_cmr_dly/_hist` (manual) |
| `ml_mora_consumo` | ✓ | ✓ | ✓ V1 (+ extra renegociado) | ✓ | `report_ml_mora_consumo_*` + `report_ml_mora_consumo_renegociado_*` |
| `ml_mora_cae` | ✓ | ✓ | ✓ V1 | ✓ | `report_ml_mora_cae_dly/_hist` |
| `ml_mora_hipotecario` | ✓ | ✓ | ✓ V1 | ✓ | `report_ml_mora_hipotecario_dly/_hist` |
| `ml_mora_comercial` | ✓ | ✓ | ✓ V1 | ✓ | `report_ml_mora_comercial_dly/_hist` |
| `ml_nmd` | ✓ | ✓ | ✓ V2 | ✓ | `report_ml_nmd_dly/_hist` |
| `ml_lc` | ✓ | ✓ | ✓ V2 | ✓ | `report_ml_lc_dly/_hist` |
| `ml_inversiones` | ✓ | ✓ | ✓ V2 | ✓ | `report_ml_inversiones_dly/_hist` |
| **`mr_ssv`** | ✓ | **✗ FALTA** | ✓ V2 | ✓ | `report_mr_ssv_dly/_hist` (manual) |

**Hallazgo principal**: `mr_ssv` no aparece en `dashboard/pages/3_Comparacion.py:18-30` (`TABLAS_HIST`) ni en `:46-58` (`NOMBRES_TABLAS`) — está en `theme.py` y en `email_report.py` pero falta en el catálogo de la comparativa.

---

## 2. Listas hardcoded de modelos — drift confirmado

| Archivo:línea | Lista | Contiene SSV | Contiene productos V2 |
|---|---|---|---|
| `core/orquestador.py:23-123` | `self.modelos` (11 entries) | ✓ | n/a |
| `dashboard/utils/theme.py:19-31` | `MODELOS_CANONICOS` | ✓ | n/a |
| `dashboard/pages/3_Comparacion.py:18-30` | `TABLAS_HIST` | ✗ | n/a |
| `dashboard/pages/3_Comparacion.py:32-41` | `CODIGO_PRODUCTOS` (8 productos) | n/a | ✗ |
| `dashboard/pages/3_Comparacion.py:46-58` | `NOMBRES_TABLAS` | ✗ | n/a |
| `core/email_report.py:46-54` | `TABLAS_PRIMERA_VUELTA` (7 tablas V1) | n/a | n/a |
| `core/email_report.py:56-62` | `TABLAS_SEGUNDA_VUELTA` (5 tablas V2) | ✓ | n/a |
| `core/email_report.py:74-83` | `CODIGO_PRODUCTOS` (8 productos) | n/a | ✗ |

**Lecciones**:
- Cuando se agregó `mr_ssv` (commit `c9e043d`) se actualizó orquestador, theme.py, email_report.py, pero no `3_Comparacion.py`. Drift inevitable sin fuente única.
- `CODIGO_PRODUCTOS` excluye productos de V2: la comparativa y el email solo cubren productos de mora (8 productos) aunque las tablas V2 estén listadas. SSV/NMD/LC/Inversiones/Prepago tienen sus propios `CODIGO_PRODUCTO` que no entran en el filtro.

---

## 3. Sistema actual de controles

### Lo que existe
- `core/control_interfaces.py` (1218 líneas): valida **pre-ejecución** archivos PML GCP/CMR. Patrón maduro de severidad (`OK/WARNING/CRITICAL`), dataclasses `Alerta`, función `evaluar_umbrales` (`:691-731`). Compara métricas `CAPITAL`, `INTERES`, `REGISTROS` agrupadas por sistema/moneda contra día anterior. Reutilizable como template.
- `core/preflight.py` (300 líneas): verifica conectividad UNC, accesibilidad de Excel, drivers ODBC.
- `core/reporte_ejecucion.py` (352 líneas): consolida tiempos, status, benchmarks por fase/modelo, alertas. Persiste en JSON local + BQ `reportes_ejecucion`.
- `core/sync_benchmark.py` (201 líneas): sincroniza duraciones por modelo a BQ `reportes_benchmark`.
- `core/email_report.py` (744 líneas): genera email con comparación amortización t vs t-1, charts plotly, Excel adjunto. Solo amortización; sin validaciones de integridad ni cuadratura.

### Lo que NO existe (gaps que abordamos)
- **Validación post-carga de outputs en BQ**: nadie chequea que el output del modelo sea consistente con su input. Esto es el "error grueso" — desbalance capital input vs `SUM(AMORTIZACION)` output pasó sin detección.
- **Conteo de filas vs historial**: si un modelo genera 10× más filas que ayer, no hay alerta.
- **Nulls en columnas required**: `CODIGO_EMPRESA` está NULLABLE en BQ aunque la regla operativa es siempre `= 1` (Banco Falabella). Hubo un fix puntual (`18e15dc`) por `NaN` en mora.
- **Productos desaparecidos**: si un `CODIGO_PRODUCTO` deja de aparecer entre t-1 y t, no se reporta.
- **Schema check**: cambios de estructura en el output pasan desapercibidos.
- **Cardinalidad de modelos ejecutados**: si solo corren 8 de 11 modelos esperados, no hay alerta automática.
- **Scoring consolidado**: cada subsistema (preflight, control_interfaces, reporte_ejecucion, email_report, sync_benchmark) opera aislado. No hay un nivel global ni dashboard único.

---

## 4. Rendimiento del dashboard

Medido en código (no en runtime). Esperamos reducción ≥30% del cold-start tras F32.

### Bottlenecks identificados
- **`dashboard/pages/3_Comparacion.py:65-70`**: UNION ALL de 11 tablas completas para listar fechas. Sin `LIMIT`.
- **`dashboard/pages/1_Home.py:109-166`**: `_consolidar_dia()` no está cacheada; se re-ejecuta en cada rerun de Streamlit.
- **`dashboard/pages/3_Comparacion.py:148-171`**: `pd.merge` + cálculo de `DIFERENCIA_%` (lambda con `axis=1`) sin caché.
- **`dashboard/pages/4_Benchmark.py:91-150`**: `_entries_a_df()` y `_agregar_por_dia()` sin caché.
- **Imports pesados a nivel módulo**:
  - `dashboard/app.py:22-25` — `plotly.graph_objects` en boot.
  - `pages/3_Comparacion.py:9` — `plotly.graph_objects`.
  - `pages/4_Benchmark.py:12-13` — `plotly.express` + `plotly.graph_objects`.
  - `pages/5_Parametros.py:14` — `deepdiff` aunque solo se usa en expander.
  - `pages/6_Email.py:10` — `plotly.graph_objects`.
  - `pages/2_Logs.py:14` — `plotly.express`.

### Lo que SÍ está bien
- `@st.cache_resource` en `dashboard/utils/bq_client.py:21-29` para cliente BQ.
- `@st.cache_data(ttl=120)` aplicado en `_fechas_disponibles_bq`, `_fechas_ejecucion_disponibles_bq`, `_cargar_todos_logs_bq`, `_cargar_reportes_fecha_bq`, `_cargar_benchmarks_bq`.

---

## 5. Contexto operativo de modelos manuales

### `mr_ssv` (manual EOM)
- Frecuencia: mensual (último día hábil del mes).
- Input: `RF_Modelo_MR_SSV/parametros/agregar_core_hardcode.py` hardcodea saldos CORE en `parametros_mr_ssv.xlsx/json`. El script se corre manualmente por @vlandaetat.
- Output: se carga a BQ vía scripts en `carga_modelos_gcp/` y `tools/`.
- F27 (backlog) planea automatizar la lectura CORE.

### `mr_prepago_cmr` (manual diario)
- Hoy se sube a BQ desde el notebook productivo `Generador_Prepago_TC_CMR_Productivo.ipynb`.
- El modelo automatizado `RF_Modelo_Prepago_CMR/mr_prepago_cmr.py` no cuadra con el notebook; ver `docs/feats/cuadre-mr-prepago-cmr/hallazgos.md`.
- Diferencias conocidas: cuotas MORA descartadas, día facturación 28/29→30 condicional, calendario N×90 distinto, SMM unit por validar.

### Implicancias para el motor de controles
- F29 trabaja **post-carga BQ** (no asume ejecución desde orquestador).
- Para SSV y CMR, en `cuadratura_inputs` aplicamos `tipo: manual` → omite cuadratura, registra INFO.
- Cuando F27 y el cuadre CMR cierren, se cambia a `tipo: access` u otro y el motor empieza a validar cuadratura sin más cambios.

---

## 6. Schema base de outputs (referencia)

Función `crear_esquema_base()` en `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py:28-61` define el esquema común a todos los outputs de modelo:

```
FECHA_PROCESO             DATE       REQUIRED
CODIGO_EMPRESA            INTEGER    NULLABLE    ← invariante: =1
OPERACION                 INTEGER    NULLABLE
COD_ACT_PAS               STRING     NULLABLE
MONEDA_ORIGEN             STRING     NULLABLE    ← {CLP, CLF, USD}
MONEDA_COMPENSACION       STRING     NULLABLE
COMPENSACION              INTEGER    NULLABLE
CODIGO_PRODUCTO           STRING     REQUIRED
CODIGO_SUBPRODUCTO        STRING     REQUIRED
FECHA_CREACION            DATE       NULLABLE
NUMERO_CUOTA              INTEGER    NULLABLE
FECHA_INICIO_CUOTA        DATE       NULLABLE
FECHA_VENCIMIENTO_CUOTA   DATE       NULLABLE
FECHA_PAGO                DATE       NULLABLE
FECHA_REPRICING           DATE       NULLABLE
AMORTIZACION              FLOAT      NULLABLE
INTERES                   FLOAT      NULLABLE
INTERES_DEVENGADO         FLOAT      NULLABLE
VP_AMORTIZACION           FLOAT      NULLABLE
VP_INTERES                FLOAT      NULLABLE
FACTOR_DE_RIESGO          STRING     NULLABLE
TIPO_CUOTA                INTEGER    NULLABLE
AREA_NEGOCIO              STRING     NULLABLE
CODIGO_EJECUTIVO          STRING     NULLABLE
CODIGO_ESTRATEGIA         STRING     NULLABLE
CLASIFICACION_CONTABLE    STRING     NULLABLE
TIPO_TASA                 INTEGER    NULLABLE
INDEXADOR                 STRING     NULLABLE
TASA                      FLOAT      NULLABLE    ← rango [0, 1]
TASA_CF                   FLOAT      NULLABLE
SPREAD                    FLOAT      NULLABLE
FECHA_ACTUALIZACION       DATETIME   NULLABLE
```

Las columnas clave para F29:
- **Cuadratura**: `AMORTIZACION` (output) vs CAPITAL del input; `INTERES` (output) vs INTERES del input.
- **Invariantes**: `CODIGO_EMPRESA`, `MONEDA_ORIGEN`, `MONEDA_COMPENSACION`, `TASA`.
- **Required**: `FECHA_PROCESO`, `CODIGO_PRODUCTO`, `CODIGO_SUBPRODUCTO`. `CODIGO_EMPRESA` debería ser REQUIRED pero está NULLABLE — gap conocido, no se cambia ahora (decisión 2026-05-13).

---

## 7. Convención de tablas BQ

Convención general: `report_{key_modelo}_dly` (diario) y `report_{key_modelo}_hist` (histórico).

Excepción única: `ml_mora_consumo` produce DOS tablas:
- `report_ml_mora_consumo_dly` / `_hist`
- `report_ml_mora_consumo_renegociado_dly` / `_hist`

Ver `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py:399-411` (mapping `MODELO_A_TABLAS`). El registry F28 modela esto vía `_TABLAS_EXTRA`.

---

## 8. Commits recientes relevantes

| Commit | Fecha | Impacto |
|---|---|---|
| `18e15dc` | 2026-05-05 | `fix(modelos): CODIGO_EMPRESA=1 en mora y MONEDA_COMPENSACION=MONEDA en NMD`. Fix paralelo (no es el "error grueso" principal). |
| `d8f69f4` | 2026-04-29 | `fix: homologación de columnas FECHA_PAGO y FECHA_REPRICING` en prepago hipotecario. |
| `c9e043d` | 2026-04-27 | Merge de modelo SSV diario productivo. Aquí se agregó `mr_ssv` en orquestador, theme, email — pero NO en comparativa. |
| `913bf0f` | 2026-04-06 | Nuevo `control_interfaces.py` (1218 líneas). Patrón de severidad maduro, base para F29. |
| `7afde01` | 2026-05-12 | Caché para Access de segunda vuelta. |

El error grueso (desbalance input↔output capital) no tiene commit propio porque no hay fix todavía — F29 lo cierra.
