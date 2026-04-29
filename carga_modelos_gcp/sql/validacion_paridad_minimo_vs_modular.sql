-- =====================================================================
-- Validación: Opción A (mínimo) vs Opción B (modular) — vista HIST
-- =====================================================================
-- Objetivo: confirmar que ambas vistas producen EXACTAMENTE el mismo
-- conjunto de filas y mismas columnas. El conteo debe dar 0 en ambos
-- lados (o sea: cero filas en A que no estén en B, y viceversa).
--
-- Uso:
--   1. Crear las dos versiones en vistas distintas (sufijo _v_minimo y
--      _v_modular) para no pisar la productiva mientras se valida:
--
--        CREATE OR REPLACE VIEW `...svw_report_modelos_hist_v_minimo`  AS <Opción A>
--        CREATE OR REPLACE VIEW `...svw_report_modelos_hist_v_modular` AS <Opción B>
--
--   2. Correr este query. Esperado: solo_en_A = 0, solo_en_B = 0.
--   3. Una vez validado, descartar las dos vistas _v_* y aplicar la
--      elegida sobre `svw_report_modelos_hist`.
--
-- Nota: EXCEPT DISTINCT requiere que ambos lados tengan el mismo
-- esquema (mismas columnas, mismos tipos, mismo orden). Si reclama
-- diferencia de esquema, ya hay un problema antes de mirar datos.
-- =====================================================================

WITH
A AS (
  SELECT * FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist_v_minimo`
),
B AS (
  SELECT * FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist_v_modular`
),
solo_en_A AS (SELECT * FROM A EXCEPT DISTINCT SELECT * FROM B),
solo_en_B AS (SELECT * FROM B EXCEPT DISTINCT SELECT * FROM A)
SELECT
  (SELECT COUNT(*) FROM A)         AS filas_A,
  (SELECT COUNT(*) FROM B)         AS filas_B,
  (SELECT COUNT(*) FROM solo_en_A) AS solo_en_A,   -- debe ser 0
  (SELECT COUNT(*) FROM solo_en_B) AS solo_en_B;   -- debe ser 0

-- =====================================================================
-- Validación complementaria: distribución por ORIGEN y banda.
-- Útil para detectar diferencias parciales (p.ej. una banda mal mapeada).
-- =====================================================================
/*
SELECT 'A' AS fuente, ORIGEN, BANDA_R13_CMF, BANDA_C46_CMF, COUNT(*) AS n
FROM A GROUP BY 1,2,3,4
UNION ALL
SELECT 'B', ORIGEN, BANDA_R13_CMF, BANDA_C46_CMF, COUNT(*)
FROM B GROUP BY 1,2,3,4
ORDER BY ORIGEN, BANDA_R13_CMF, BANDA_C46_CMF, fuente;
*/

-- =====================================================================
-- Validación contra la vista actual en producción (sanity check).
-- Limita por fecha y excluye los modelos nuevos (no existen en la
-- vista vieja). Esperado: solo_en_vieja = 0, solo_en_nueva = 0.
-- =====================================================================
/*
WITH
nueva AS (
  SELECT * FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist_v_minimo`
  WHERE FECHA_PROCESO = DATE '2026-04-25'
    AND ORIGEN NOT IN ('report_ml_nmd_hist',
                       'report_ml_inversiones_hist',
                       'report_ml_lc_hist',
                       'report_mr_ssv_hist')
),
vieja AS (
  SELECT * FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist`
  WHERE FECHA_PROCESO = DATE '2026-04-25'
)
SELECT
  (SELECT COUNT(*) FROM vieja EXCEPT DISTINCT SELECT * FROM nueva) AS solo_en_vieja,
  (SELECT COUNT(*) FROM nueva EXCEPT DISTINCT SELECT * FROM vieja) AS solo_en_nueva;
*/
