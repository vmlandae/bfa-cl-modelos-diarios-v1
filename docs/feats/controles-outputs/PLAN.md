# Sprint S6-2026: Controles & Cobertura Dashboard — PLAN

> **Tamaño:** Sprint multi-feature (F28-F32) · **Asignado:** @vlandaetat · **Inicio:** 2026-05-14 · **Fin estimado:** 2026-05-30
> **Rama maestra:** `feat/sprint-s6-controles`
> **Fuente:** [roadmap.yaml — sprint S6-2026](../../roadmap/roadmap.yaml)
> **Diagnóstico previo:** [hallazgos.md](hallazgos.md)

---

## Contexto y motivación

El sprint nace de dos hechos:

1. **Error grueso reciente**: hubo una diferencia entre el capital de entrada (PML/Access/Excel input) y la suma de `AMORTIZACION` del output del modelo. Ningún control automático lo detectó. El "error grueso" no fue `CODIGO_EMPRESA=NaN` (commit `18e15dc`, fix paralelo), sino **desbalance input↔output de montos** que requiere validación de cuadratura.
2. **Dashboard y email no cubren todos los modelos**: `mr_ssv` falta en `dashboard/pages/3_Comparacion.py` aunque ya está en orquestador y `email_report`. El filtro `CODIGO_PRODUCTOS` hardcoded deja fuera productos de V2 (NMD, LC, Inversiones, SSV, Prepago).

**Contexto operativo importante** (confirmado 2026-05-13):
- `mr_ssv` y `mr_prepago_cmr` se corren **manualmente** hoy (Excel y notebook respectivamente). Outputs se suben a BQ con scripts dedicados.
- Ver [`docs/feats/cuadre-mr-prepago-cmr/hallazgos.md`](../cuadre-mr-prepago-cmr/hallazgos.md): el modelo automatizado CMR diverge del notebook productivo (filas MORA descartadas, SMM unit por validar, +210 filas extra). Por eso se mantiene flujo manual.
- El motor de controles trabaja contra BQ post-carga, sea automática o manual. La cuadratura input↔output aplica solo donde haya input automatizable.

---

## Decisiones tomadas (2026-05-13)

| Decisión | Elección |
|---|---|
| Ritmo | Lento y verificado, no urgente |
| Política CRITICAL | No degrada `status_global`. Solo log + email + página Controles + subject `[CRITICO]` |
| Estructura email | Email único con secciones V1/V2 (en lugar de dos correos separados) |
| Hardening BQ | No tocar schema ahora; validaciones en writers se difieren a sprint posterior |
| Check principal | Cuadratura input↔output (capital + interés) para modelos automatizados |
| SSV/Prepago_CMR | Mantener flujo manual; motor solo aplica checks de output (no cuadratura) |

---

## Features del sprint

| ID | Título | Tamaño | Prioridad | Dependencias |
|----|--------|--------|-----------|--------------|
| F28 | Fuente única de modelos (`modelos_registry`) | S | alta | — |
| F29 | Motor de controles con cuadratura | L | crítica | F28 |
| F30 | Email unificado con sección de salud | M | alta | F28, F29 |
| F31 | Dashboard página Controles + banner Home | M | alta | F28, F29 |
| F32 | Performance dashboard (quick wins) | S | media | F28 |

---

## Plan por fases

### Fase 1 — Preparación (medio día)
- Crear rama `feat/sprint-s6-controles`. ✅
- Actualizar `roadmap.yaml` con sprint S6 y features F28-F32. ✅
- Crear este `PLAN.md` y `hallazgos.md`. ✅
- Commit: `roadmap: planificar sprint S6 — Controles & Cobertura Dashboard`.

### Fase 2 — F28 + F32 (2-3 días)
F28 desbloquea SSV en comparativa; F32 mejora perf inmediatamente.

1. **`core/modelos_registry.py`** — fuente única con API pública.
2. **Adopción**:
   - `core/orquestador.py:23-123` → `from core.modelos_registry import _MODELOS`.
   - `core/email_report.py:46-83` → consumir registry; eliminar `CODIGO_PRODUCTOS`.
   - `dashboard/utils/theme.py:19-31` → derivar `MODELOS_CANONICOS`.
   - `dashboard/pages/3_Comparacion.py:18-58,32-41` → derivar `TABLAS_HIST`, `NOMBRES_TABLAS`; eliminar `CODIGO_PRODUCTOS`.
   - `main.py:60-73` → `MODELO_A_TABLAS` desde registry.
   - `core/reporte_ejecucion.py:97-104` → `_VUELTA_*` desde registry.
3. **Quick wins F32**:
   - Lazy imports plotly/deepdiff en `dashboard/app.py:22-25` y pages.
   - `_consolidar_dia(fecha_iso)` cacheable en `1_Home.py:109-281`.
   - `_comparar(fecha_t, fecha_t1)` cacheado en `3_Comparacion.py:148-171`.
   - `LIMIT 60` + TTL 900 en `obtener_fechas_disponibles` (`3_Comparacion.py:77-86`).
   - Columna sintética `MODELO` en `_union_all_tablas()` (`3_Comparacion.py:65-114`).
   - Cache pipeline benchmark (`4_Benchmark.py:91-150`).
4. **Tests**: smoke registry, navegar todas las páginas, verificar SSV en comparativa.
5. **Commits**:
   - `feat(registry): fuente única de modelos`
   - `refactor(orquestador,dashboard,email): consumir modelos_registry`
   - `fix(comparativa): agregar mr_ssv y columna modelo`
   - `perf(dashboard): lazy imports y cache de transformaciones`

### Fase 3 — F29 motor mínimo (3-4 días)
Solo checks que dependen del output BQ (sin cuadratura todavía).

1. `core/controles_outputs.py` con dataclasses `CheckResultado`, `ResultadoControles` y motor de checks.
2. Checks 4-10 (n_filas, nulls_required, invariantes, productos_desaparecidos, freshness, delta_amort/interes).
3. `core/controles_persistence.py` con tabla `controles_diarios` (particionada, clusterizada).
4. Sección `controles:` mínima en YAML (sin `cuadratura_inputs`).
5. CLI `python -m core.controles_outputs --fecha YYYY-MM-DD [--modelos ...] [--no-persist] [--export-json ...]`.
6. Verificar contra fechas históricas.
7. Commit: `feat(controles): motor de checks post-carga con persistencia BQ`.

### Fase 4 — F29 cuadratura (3-4 días)
1. `core/controles_cuadratura.py` para modelos PML (mora + prepago consumo/hipotecario), reutiliza lectores de `control_interfaces.py:169-178`.
2. Sección `cuadratura_inputs` en YAML.
3. Modelos Access (NMD, LC, Inversiones): lectores parametrizables.
4. Modelos manuales (SSV, CMR): `tipo: manual` (registran INFO).
5. **Reproducir el error grueso** con datos históricos o test sintético.
6. Commit: `feat(controles): cuadratura input↔output capital e interés`.

### Fase 5 — F29 hook orquestador (1 día)
1. `OrquestadorModelos.ejecutar_controles_post_carga(modelos, fecha)`.
2. Invocación desde `main.py:307-330` después de carga GCP.
3. `ReporteEjecucion.registrar_controles(resultado)` + entradas `[CONTROL CRITICO]` en `_alertas`. NO degradar `status_global`.
4. End-to-end con ejecución real.
5. Commit: `feat(orquestador): hook de controles post-carga`.

### Fase 6 — F30 email unificado (2-3 días)
1. Tipo `unificado` agregado a `_TABLAS_POR_TIPO`.
2. `_construir_seccion_salud()`, `_construir_anexo_criticos()`, `_construir_tabla_maestra()`.
3. Refactor `_construir_html()` en bloques.
4. CLI `--preview-html`.
5. Subject `[CRITICO]` cuando aplica.
6. Comparar HTML antes/después con datos reales.
7. Commit: `feat(email): reporte unificado con sección de salud y cobertura completa`.

### Fase 7 — F31 dashboard Controles (2 días)
1. `dashboard/utils/controles_helpers.py`.
2. `dashboard/pages/7_Controles.py`.
3. Mini-banner en `1_Home.py:197-209`.
4. `n_no_ejec` (`1_Home.py:313-315`) usa `listar_modelos()`.
5. Verificación visual con fechas que tienen WARN/CRIT.
6. Commit: `feat(dashboard): página Controles + banner Home`.

### Fase 8 — Cierre (medio día)
1. Revisar criterios de aceptación de cada feature.
2. Actualizar `roadmap.yaml` estados a `completado`.
3. MR/merge final a `main`.

---

## Plan de verificación (consolidado)

### V1. Smoke registry
```bash
python -c "
from core.modelos_registry import listar_modelos, todas_las_tablas_hist, tablas_extra_hist
print('modelos:', listar_modelos())
print('V1:', todas_las_tablas_hist(vuelta=1))
print('V2:', todas_las_tablas_hist(vuelta=2))
print('extras mora_consumo:', tablas_extra_hist('ml_mora_consumo'))
"
```
Esperado: 11 modelos; V1=7 tablas (incluye `report_ml_mora_consumo_renegociado_hist`); V2=5 (incluye `report_mr_ssv_hist`).

### V2. Cold-start dashboard
```bash
time streamlit run dashboard/app.py --server.headless=true --server.port=8501
```
Objetivo F32: reducción ≥30% vs baseline.

### V3. Comparativa cobertura
Navegar a Comparación. Confirmar selector incluye `SSV (EOM)`. Gráficos por moneda cubren productos de NMD/LC/Inversiones/SSV/Prepago.

### V4. Controles standalone
```bash
python -m core.controles_outputs --fecha 2026-05-12
python -m core.controles_outputs --fecha 2026-05-12 --modelos ml_mora_consumo --export-json /tmp/ctrl.json --no-persist
```

### V5. Reproducir el error grueso
Fecha histórica con desbalance conocido (o test sintético en `2099-01-01`). Validar `cuadratura_capital` lo marca CRITICAL.

### V6. Email preview
```bash
python -m core.email_report --fecha 2026-05-12 --tipo unificado --preview-html
```
Resultado: `reports/20260512/email_preview_unificado/index.html` con sección de salud, tabla maestra, secciones por modelo. Sin Outlook.

### V7. Página Controles
Navegar a `7_Controles`. Validar tiles, matriz pivote, drill-down.

### V8. End-to-end
```bash
python main.py --modelos primera_vuelta --fecha 2026-05-13 --cargar-gcp
```
Validar `controles` en reporte, escritura a `controles_diarios`, email con sección de salud.

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cuadratura difícil en modelos V2 (Access) | Fase 3 cubre PML (mora + prepago V1). Fase 4 amplía Access. Manuales (SSV/CMR) con `tipo: manual`. |
| Tabla `controles_diarios` no existe el primer día | `crear_tabla_si_no_existe()` desde la primera escritura. Fallback local. |
| Refactor email rompe envío diario | `unificado` como tipo NUEVO sin tocar `primera_vuelta`/`segunda_vuelta`. Activar vía flag YAML cuando se valide. |
| Cache `_consolidar_dia` requiere refactor de firma | Refactor mínimo: `(fecha_iso: str)` y mover query adentro. |
| Modelos manuales faltan algún día | `cuadratura_inputs.{modelo}.tipo: manual` los excluye. Si tabla no existe → `n_filas_zero` CRIT informa. |

---

## Esquema BQ `controles_diarios`

Dataset: `bfa_cl_prd_financial_risk_dly_proc_models`
Particionada por `fecha_proceso`, clusterizada por `(modelo, nivel)`.

| Campo | Tipo | Modo |
|---|---|---|
| `fecha_proceso` | DATE | REQUIRED |
| `timestamp` | TIMESTAMP | REQUIRED |
| `hostname` | STRING | REQUIRED |
| `modelo` | STRING | REQUIRED |
| `tabla` | STRING | NULLABLE |
| `check_id` | STRING | REQUIRED |
| `nivel` | STRING | REQUIRED |
| `mensaje` | STRING | NULLABLE |
| `evidencia_json` | STRING | NULLABLE |
| `fecha_anterior` | DATE | NULLABLE |
| `version_motor` | STRING | NULLABLE |

---

## Catálogo de checks (F29)

| `check_id` | Descripción | Severidad |
|---|---|---|
| `cuadratura_capital` | `SUM(CAPITAL_input)` vs `SUM(AMORTIZACION_output)` por modelo×moneda. WARNING >0.1%, CRITICAL >1%. | WARN/CRIT |
| `cuadratura_interes` | Análogo a `cuadratura_capital` para INTERES. | WARN/CRIT |
| `delta_amort_<moneda>` | Variación de `SUM(AMORT)` vs día anterior. Default WARN 5%, CRIT 15%. | WARN/CRIT |
| `delta_interes_<moneda>` | Análogo para INTERES. | WARN/CRIT |
| `n_filas_ratio` | `n_filas(t)/n_filas(t-1)` fuera de `[0.5,2.0]` WARN; fuera de `[0.3,3.0]` CRIT. | WARN/CRIT |
| `n_filas_zero` | `n_filas(t) == 0`. | CRIT |
| `nulls_required` | NULL en `FECHA_PROCESO`, `CODIGO_PRODUCTO`, `CODIGO_SUBPRODUCTO`. | CRIT |
| `invariante_codigo_empresa` | `CODIGO_EMPRESA` debe ser único valor = 1. | CRIT |
| `invariante_monedas` | `MONEDA_ORIGEN`, `MONEDA_COMPENSACION` ∈ {CLP, CLF, USD}. | WARN/CRIT |
| `productos_desaparecidos` | Productos presentes ayer y ausentes hoy. | CRIT |
| `freshness_fecha` | `FECHA_PROCESO == @fecha` consultada. | CRIT |

---

## Sección YAML propuesta

```yaml
controles:
  enabled: true
  version_motor: "1.0"
  defaults:
    cuadratura:
      tolerancia_pct: { warning: 0.1, critical: 1.0 }
    nulls_required:
      campos: ["FECHA_PROCESO", "CODIGO_PRODUCTO", "CODIGO_SUBPRODUCTO"]
      nivel: "CRITICAL"
    invariantes:
      codigo_empresa: [1]
      monedas_validas: ["CLP", "CLF", "USD"]
    n_filas:
      warning_ratio: [0.5, 2.0]
      critical_ratio: [0.3, 3.0]
    delta:
      warning_pct: 5.0
      critical_pct: 15.0
  por_modelo:
    ml_inversiones:
      delta: { warning_pct: 10.0, critical_pct: 30.0 }
    ml_mora_consumo:
      delta: { critical_pct: 8.0 }
  cuadratura_inputs:
    ml_mora_consumo:        { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    ml_mora_cae:            { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    ml_mora_hipotecario:    { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    ml_mora_comercial:      { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    mr_prepago_consumo:     { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    mr_prepago_hipotecario: { tipo: "pml_gcp", columna_capital: "CAPITAL", columna_interes: "INTERES" }
    ml_nmd:                 { tipo: "access",  ruta_tabla: "Balance_NMD", columna_capital: "SALDO_CAPITAL" }
    ml_lc:                  { tipo: "access",  ruta_tabla: "Balance_LC",  columna_capital: "SALDO_CAPITAL" }
    ml_inversiones:         { tipo: "access",  ruta_tabla: "Balance_INV", columna_capital: "SALDO_CAPITAL" }
    mr_ssv:                 { tipo: "manual",  nota: "EOM, input subido desde Excel hardcoded — F27" }
    mr_prepago_cmr:         { tipo: "manual",  nota: "Notebook productivo subido a BQ — ver docs/feats/cuadre-mr-prepago-cmr/hallazgos.md" }
```

---

## Archivos críticos

### Nuevos
- `core/modelos_registry.py` (F28)
- `core/controles_outputs.py` (F29)
- `core/controles_cuadratura.py` (F29)
- `core/controles_persistence.py` (F29)
- `dashboard/pages/7_Controles.py` (F31)
- `dashboard/utils/controles_helpers.py` (F31)

### Editar
- `core/orquestador.py` (F28, F29)
- `core/email_report.py` (F28, F30)
- `core/reporte_ejecucion.py` (F28, F29)
- `main.py` (F28, F29)
- `dashboard/utils/theme.py` (F28)
- `dashboard/pages/1_Home.py` (F31, F32)
- `dashboard/pages/3_Comparacion.py` (F28, F32)
- `dashboard/pages/4_Benchmark.py` (F32)
- `dashboard/app.py` (F31, F32)
- `config/config_rutas_ext_y_archivos.yaml` (F29, F30)
- `docs/roadmap/roadmap.yaml` (Fase 1, Fase 8)
