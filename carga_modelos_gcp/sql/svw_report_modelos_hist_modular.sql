-- =====================================================================
-- Vista: svw_report_modelos_hist  (Opción B — refactor modular)
-- =====================================================================
-- Equivalente exacta a la vista de Opción A. Cambios estructurales:
--   1. Catálogos R13/C46 como CTE de filas (UNNEST de STRUCTs).
--   2. Mapa ORIGEN → tipo de banda en una sola CTE (única fuente de verdad,
--      antes duplicada en los 4 CASE).
--   3. Bandas y glosas se obtienen vía LEFT JOIN contra los catálogos.
--
-- Para agregar un modelo nuevo:
--   - 1 fila en `base_union` (línea SELECT *, '<tabla>' AS ORIGEN FROM ...)
--   - 1 fila en `origen_banda` con su tipo (R13 / C46 / o sin entrada si no aplica)
--
-- Para modificar/agregar bandas regulatorias:
--   - 1 fila en `r13_bands` o `c46_bands` (banda + glosa + lo + hi).
--
-- Semántica preservada bit-a-bit respecto a la vista original:
--   - R13: rangos [lo, hi) — lo inclusive, hi exclusive.
--   - C46: rangos [lo, hi] — ambos inclusive.
--   - Último tramo abierto se modela con hi = NULL.
--   - Glosa para origenes sin tipo de banda → 'NO_APLICA' (igual que ELSE actual).
--   - Banda numérica para origenes sin tipo de banda → NULL.
--
-- Dataset: bfa_cl_prd_financial_risk_dly_proc_models_hist
-- =====================================================================

CREATE OR REPLACE VIEW `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist` AS
WITH
-- ─────────────────────────────────────────────────────────────────────
-- 1. Catálogo R13 (Circular 3.565, capítulo 13)
--    Rangos [lo, hi) semi-abiertos. hi = NULL → tramo abierto al infinito.
-- ─────────────────────────────────────────────────────────────────────
r13_bands AS (
  SELECT * FROM UNNEST([
    STRUCT( 1 AS banda, 'Overnight'           AS glosa,    0 AS lo,                   1 AS hi),
    STRUCT( 2,          'Overnight < t ≤ 1M',              1,                         30),
    STRUCT( 3,          '1M < t ≤ 3M',                     30,                        90),
    STRUCT( 4,          '3M < t ≤ 6M',                     90,                        180),
    STRUCT( 5,          '6M < t ≤ 9M',                     180,                       270),
    STRUCT( 6,          '9M < t ≤ 1A',                     270,                       360),
    STRUCT( 7,          '1A < t ≤ 1,5A',                   360,                       540),
    STRUCT( 8,          '1,5A < t ≤ 2A',                   540,                       720),
    STRUCT( 9,          '2A < t ≤ 3A',                     720,                       1080),
    STRUCT(10,          '3A < t ≤ 4A',                     1080,                      1440),
    STRUCT(11,          '4A < t ≤ 5A',                     1440,                      1800),
    STRUCT(12,          '5A < t ≤ 6A',                     1800,                      2160),
    STRUCT(13,          '6A < t ≤ 7A',                     2160,                      2520),
    STRUCT(14,          '7A < t ≤ 8A',                     2520,                      2880),
    STRUCT(15,          '8A < t ≤ 9A',                     2880,                      3240),
    STRUCT(16,          '9A < t ≤ 10A',                    3240,                      3600),
    STRUCT(17,          '10A < t ≤ 15A',                   3600,                      5400),
    STRUCT(18,          '15A < t ≤ 20A',                   5400,                      7200),
    STRUCT(19,          't > 20A',                         7200,                      CAST(NULL AS INT64))
  ])
),

-- ─────────────────────────────────────────────────────────────────────
-- 2. Catálogo C46 (CMF C46 — bandas de mora)
--    Rangos [lo, hi] inclusivos. hi = NULL → tramo abierto al infinito.
--    Los días 2..7 se modelan como tramos [n,n] (equivalente a "= n").
-- ─────────────────────────────────────────────────────────────────────
c46_bands AS (
  SELECT * FROM UNNEST([
    STRUCT(101 AS banda, 'Primer día'                   AS glosa,   0 AS lo,           1 AS hi),
    STRUCT(102,          'Segundo día',                              2,                2),
    STRUCT(103,          'Tercer día',                               3,                3),
    STRUCT(104,          'Cuarto día',                               4,                4),
    STRUCT(105,          'Quinto día',                               5,                5),
    STRUCT(106,          'Sexto día',                                6,                6),
    STRUCT(107,          'Séptimo día',                              7,                7),
    STRUCT(205,          'Desde 8 hasta 15 días.',                   8,                15),
    STRUCT(310,          'Desde 16 hasta 30 días.',                  16,               30),
    STRUCT(415,          'Desde 31 hasta 60 días.',                  31,               60),
    STRUCT(520,          'Desde 61 hasta 90 días.',                  61,               90),
    STRUCT(625,          'Desde 91 hasta 180 días.',                 91,               180),
    STRUCT(730,          'Desde 181 días hasta un año.',             181,              365),
    STRUCT(831,          'Mayor a 1 año',                            366,              CAST(NULL AS INT64))
  ])
),

-- ─────────────────────────────────────────────────────────────────────
-- 3. Mapa ORIGEN → tipo de banda CMF (R13 | C46)
--    Modelos sin entrada acá tendrán BANDA_*_CMF=NULL y glosa='NO_APLICA'.
-- ─────────────────────────────────────────────────────────────────────
origen_banda AS (
  SELECT 'report_mr_prepago_consumo_hist'      AS ORIGEN, 'R13' AS tipo UNION ALL
  SELECT 'report_mr_prepago_hipotecario_hist',           'R13'         UNION ALL
  SELECT 'report_mr_prepago_cmr_hist',                   'R13'         UNION ALL
  SELECT 'report_mr_ssv_hist',                           'R13'         UNION ALL
  SELECT 'report_ml_mora_cae_hist',                      'C46'         UNION ALL
  SELECT 'report_ml_mora_comercial_hist',                'C46'         UNION ALL
  SELECT 'report_ml_mora_consumo_hist',                  'C46'         UNION ALL
  SELECT 'report_ml_mora_consumo_renegociado_hist',      'C46'         UNION ALL
  SELECT 'report_ml_mora_hipotecario_hist',              'C46'         UNION ALL
  SELECT 'report_ml_nmd_hist',                           'C46'         UNION ALL
  SELECT 'report_ml_inversiones_hist',                   'C46'         UNION ALL
  SELECT 'report_ml_lc_hist',                            'C46'
),

-- ─────────────────────────────────────────────────────────────────────
-- 4. Unión de todas las tablas de modelos.
--    Todas comparten el esquema de 32 columnas (verificado vía
--    INFORMATION_SCHEMA.COLUMNS), por lo que SELECT * es seguro y
--    produce el mismo orden de columnas en todas las ramas.
-- ─────────────────────────────────────────────────────────────────────
base_union AS (
  SELECT *, 'report_ml_mora_cae_hist'                AS ORIGEN
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_mora_cae_hist`
  UNION ALL SELECT *, 'report_ml_mora_comercial_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_mora_comercial_hist`
  UNION ALL SELECT *, 'report_ml_mora_consumo_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_mora_consumo_hist`
  UNION ALL SELECT *, 'report_ml_mora_consumo_renegociado_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_mora_consumo_renegociado_hist`
  UNION ALL SELECT *, 'report_ml_mora_hipotecario_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_mora_hipotecario_hist`
  UNION ALL SELECT *, 'report_ml_nmd_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_nmd_hist`
  UNION ALL SELECT *, 'report_ml_inversiones_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_inversiones_hist`
  UNION ALL SELECT *, 'report_ml_lc_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_lc_hist`
  UNION ALL SELECT *, 'report_mr_prepago_cmr_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_mr_prepago_cmr_hist`
  UNION ALL SELECT *, 'report_mr_prepago_consumo_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_mr_prepago_consumo_hist`
  UNION ALL SELECT *, 'report_mr_prepago_hipotecario_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_mr_prepago_hipotecario_hist`
  UNION ALL SELECT *, 'report_mr_ssv_hist'
    FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_mr_ssv_hist`
),

-- ─────────────────────────────────────────────────────────────────────
-- 5. Anota DIAS_VENCIMIENTO y resuelve el tipo de banda por ORIGEN.
-- ─────────────────────────────────────────────────────────────────────
base AS (
  SELECT
    b.*,
    m.tipo AS BANDA_TIPO,
    DATE_DIFF(b.FECHA_VENCIMIENTO_CUOTA, b.FECHA_PROCESO, DAY) AS DIAS_VENCIMIENTO
  FROM base_union b
  LEFT JOIN origen_banda m USING (ORIGEN)
)

-- ─────────────────────────────────────────────────────────────────────
-- 6. Resultado final
--    El orden de columnas final es:
--      [32 columnas del esquema base],
--      ORIGEN, DIAS_VENCIMIENTO,
--      BANDA_R13_CMF, GLOSA_BANDA_R13_CMF,
--      BANDA_C46_CMF, GLOSA_BANDA_C46_CMF
--    — idéntico al de la vista original.
-- ─────────────────────────────────────────────────────────────────────
SELECT
  b.* EXCEPT (BANDA_TIPO),
  IF(b.BANDA_TIPO = 'R13', r13.banda, NULL)        AS BANDA_R13_CMF,
  IF(b.BANDA_TIPO = 'R13', r13.glosa, 'NO_APLICA') AS GLOSA_BANDA_R13_CMF,
  IF(b.BANDA_TIPO = 'C46', c46.banda, NULL)        AS BANDA_C46_CMF,
  IF(b.BANDA_TIPO = 'C46', c46.glosa, 'NO_APLICA') AS GLOSA_BANDA_C46_CMF
FROM base b
LEFT JOIN r13_bands r13
  ON  b.BANDA_TIPO = 'R13'
  AND b.DIAS_VENCIMIENTO >= r13.lo
  AND (r13.hi IS NULL OR b.DIAS_VENCIMIENTO <  r13.hi)
LEFT JOIN c46_bands c46
  ON  b.BANDA_TIPO = 'C46'
  AND b.DIAS_VENCIMIENTO >= c46.lo
  AND (c46.hi IS NULL OR b.DIAS_VENCIMIENTO <= c46.hi)
