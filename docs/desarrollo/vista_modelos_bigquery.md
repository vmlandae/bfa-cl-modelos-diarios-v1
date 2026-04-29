# Vista consolidada de modelos en BigQuery

> **Autor:** vlandaetat
> **Fecha de creación:** 2026-04-29
> **Última edición por:** vlandaetat
> **Fecha última edición:** 2026-04-29

---

## Resumen

La vista `svw_report_modelos_hist` (y su equivalente `_dly`) consolida en una
sola tabla virtual el output de todos los modelos diarios que se cargan a
BigQuery. Cumple tres objetivos:

1. **Unificar** las 12 tablas `report_*_hist` en un único punto de consulta,
   agregando una columna `ORIGEN` para identificar la tabla de procedencia.
2. **Calcular** `DIAS_VENCIMIENTO = FECHA_VENCIMIENTO_CUOTA − FECHA_PROCESO`.
3. **Asignar bandas regulatorias CMF** (R13 y C46) según el modelo de origen,
   con su glosa correspondiente.

El SQL versionado vive en [`carga_modelos_gcp/sql/`](https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/tree/main/carga_modelos_gcp/sql).

---

## Ubicación en BigQuery

| | Daily | Histórico |
|---|---|---|
| **Dataset** | `bfa_cl_prd_financial_risk_dly_proc_models` | `bfa_cl_prd_financial_risk_dly_proc_models_hist` |
| **Vista** | `svw_report_modelos_dly` | `svw_report_modelos_hist` |
| **Tablas fuente** | `report_*_dly` (12) | `report_*_hist` (12) |
| **Particionado fuente** | sin partición forzada | partition por `FECHA_PROCESO` con `require_partition_filter=true` |

!!! warning "Filtro obligatorio en hist"
    Cualquier consulta a `svw_report_modelos_hist` debe filtrar por
    `FECHA_PROCESO`. Sin filtro, BigQuery rechaza el query con
    *"Cannot query over table … without a filter over column(s) 'FECHA_PROCESO'"*.
    No es una limitación de la vista sino de las tablas particionadas
    subyacentes.

---

## Mapeo modelo → banda CMF

| ORIGEN | Banda CMF |
|---|---|
| `report_mr_prepago_consumo_*` | R13 |
| `report_mr_prepago_hipotecario_*` | R13 |
| `report_mr_prepago_cmr_*` | R13 |
| `report_mr_ssv_*` | R13 |
| `report_ml_mora_cae_*` | C46 |
| `report_ml_mora_comercial_*` | C46 |
| `report_ml_mora_consumo_*` | C46 |
| `report_ml_mora_consumo_renegociado_*` | C46 |
| `report_ml_mora_hipotecario_*` | C46 |
| `report_ml_nmd_*` | C46 |
| `report_ml_inversiones_*` | C46 |
| `report_ml_lc_*` | C46 |

Los modelos sin entrada en este mapeo reciben `BANDA_*_CMF = NULL` y
`GLOSA_BANDA_*_CMF = 'NO_APLICA'`.

### Bandas R13 (Circular 3.565, capítulo 13)

19 tramos con rangos **semi-abiertos** `[lo, hi)` desde `Overnight` (banda 1)
hasta `t > 20A` (banda 19). Aplica a modelos `mr_*` (riesgo de mercado /
liquidez por vencimiento).

### Bandas C46 (CMF C46, mora)

14 tramos con rangos **inclusivos** `[lo, hi]` desde `Primer día` (banda 101)
hasta `Mayor a 1 año` (banda 831). Los días 2 a 7 se modelan como tramos
unitarios. Aplica a modelos `ml_*` (mora, NMD, inversiones, líneas).

---

## Esquema de salida

38 columnas:

- 32 columnas del esquema base (`crear_esquema_base()` en
  [`cargar_output_modelos_bigquery_dly.py`](https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/blob/main/carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py)).
- `ORIGEN` (STRING) — nombre de la tabla fuente.
- `DIAS_VENCIMIENTO` (INT64) — derivado.
- `BANDA_R13_CMF` (INT64), `GLOSA_BANDA_R13_CMF` (STRING).
- `BANDA_C46_CMF` (INT64), `GLOSA_BANDA_C46_CMF` (STRING).

---

## Dos versiones equivalentes

Hay dos archivos con el mismo SQL semántico pero distinto estilo:

### `svw_report_modelos_hist_minimo.sql` (Opción A — desplegada)

Mismo diseño que la vista original: `UNION ALL` de las 12 tablas + dos pares
de `CASE` anidados (uno por banda × código/glosa). Único cambio respecto al
original: las 32 columnas explícitas por rama se reemplazan por `SELECT *`,
válido porque todas las tablas fuente comparten el esquema base (32
columnas, mismos nombres y tipos — verificable vía `INFORMATION_SCHEMA.COLUMNS`).

Es la versión **actualmente desplegada** en BigQuery.

### `svw_report_modelos_hist_modular.sql` (Opción B — alternativa)

Refactor con tres CTEs adicionales:

- `r13_bands` — catálogo R13 como filas (`UNNEST` de `STRUCT`s).
- `c46_bands` — catálogo C46 como filas.
- `origen_banda` — mapeo `ORIGEN → tipo_banda` (única fuente de verdad).

Las bandas se asignan vía `LEFT JOIN` contra los catálogos. El resultado es
**idéntico** al de Opción A. Beneficios: agregar un modelo nuevo es 1 línea
(no 4 listas `IN (...)` distintas), y modificar una banda regulatoria es 1
fila (no 2 escaleras `CASE` separadas).

Trade-off: tiene un `LEFT JOIN` extra contra dos tablas chicas. En la
práctica el optimizador de BQ las inlining, así que el costo es nulo.

---

## Despliegue

### Reemplazo de la vista productiva

Una vista estándar de BigQuery es **virtual**: el `CREATE OR REPLACE VIEW`
guarda la definición SQL, sin materializar filas. Desde la siguiente
consulta, la vista devuelve datos con la lógica nueva contra el estado
**actual** de las tablas fuente. **No hace falta "ejecutarla" ni refrescar
nada.**

```bash
# Opción A (recomendada para cambios pequeños)
bq query --use_legacy_sql=false < carga_modelos_gcp/sql/svw_report_modelos_hist_minimo.sql

# Opción B (si se quiere migrar a la versión modular)
bq query --use_legacy_sql=false < carga_modelos_gcp/sql/svw_report_modelos_hist_modular.sql
```

### Validación post-despliegue

```sql
SELECT ORIGEN,
       COUNT(*)                       AS n_filas,
       COUNT(DISTINCT BANDA_R13_CMF)  AS n_R13,
       COUNT(DISTINCT BANDA_C46_CMF)  AS n_C46
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist`
WHERE FECHA_PROCESO BETWEEN DATE '<inicio>' AND DATE '<fin>'
GROUP BY ORIGEN
ORDER BY ORIGEN;
```

Lo esperado:

- Las 12 tablas devuelven filas (ninguna queda en cero).
- Cada `ORIGEN` tiene `n_R13 > 0` **xor** `n_C46 > 0` — nunca ambos
  positivos, nunca ambos en cero.

### Validación de paridad entre opciones A y B

Si se quiere migrar de A a B (o viceversa), usar
[`validacion_paridad_minimo_vs_modular.sql`](https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/blob/main/carga_modelos_gcp/sql/validacion_paridad_minimo_vs_modular.sql):

1. Crear ambas versiones como vistas paralelas con sufijo `_v_minimo` y
   `_v_modular` (no pisar la productiva).
2. Correr el `EXCEPT DISTINCT` cruzado del archivo. Esperado:
   `solo_en_A = 0 ∧ solo_en_B = 0`.
3. Una vez validado, descartar las dos vistas paralelas y aplicar la elegida
   sobre `svw_report_modelos_hist`.

---

## Cómo agregar un modelo nuevo

### Pre-requisito: la tabla fuente debe existir

El modelo tiene que estar primero en
[`cargar_output_modelos_bigquery_dly.py`](https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/blob/main/carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py)
y `cargar_output_modelos_bigquery_hist.py` con esquema `crear_esquema_base()`.
Sin eso, la vista no puede unirla.

### Opción A (mínimo)

Agregar **3 cambios** en el archivo:

1. **Una rama `UNION ALL`** dentro del CTE `base_union`:
   ```sql
   UNION ALL
   SELECT *, 'report_<modelo>_hist' AS ORIGEN
     FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_<modelo>_hist`
   ```

2. **Agregar el ORIGEN** a la lista `IN (...)` del `CASE` correspondiente
   (R13 o C46) — son **dos listas** que mantener (una para banda, otra para
   glosa, en cada tipo). En total 2 ediciones.

3. Reemplazar la vista con `CREATE OR REPLACE VIEW`.

### Opción B (modular)

Agregar **2 cambios**:

1. **Una rama `UNION ALL`** en `base_union` (igual que Opción A).
2. **Una fila** en el CTE `origen_banda`:
   ```sql
   SELECT 'report_<modelo>_hist',  '<R13|C46>'  UNION ALL
   ```

Sin tocar las listas `IN (...)` ni los `CASE` — la lógica de banding queda
encapsulada en los catálogos.

---

## Histórico del despliegue

| Fecha | Cambio | Trigger |
|---|---|---|
| 2026-04-29 | Se agregan 4 modelos de segunda vuelta a `svw_report_modelos_hist`: `ml_nmd`, `ml_inversiones`, `ml_lc` (C46), `mr_ssv` (R13). Se versiona el SQL en `carga_modelos_gcp/sql/`. | Paso a producción de modelos de segunda vuelta. |
