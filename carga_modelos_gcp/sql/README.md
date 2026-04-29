# SQL — Vistas consolidadas de modelos en BigQuery

Esta carpeta versiona el SQL de la vista `svw_report_modelos_hist` (y, en el
futuro, su gemela `_dly`) que consolida las 12 tablas `report_*` en una
única tabla virtual con bandas CMF R13/C46 calculadas.

**Documentación detallada:** [docs/desarrollo/vista_modelos_bigquery.md](../../docs/desarrollo/vista_modelos_bigquery.md)

## Archivos

| Archivo | Propósito |
|---|---|
| `svw_report_modelos_hist_minimo.sql` | **Vista desplegada.** Diseño igual al original (UNION ALL + CASE), con `SELECT *` por rama y los 4 modelos de segunda vuelta agregados. |
| `svw_report_modelos_hist_modular.sql` | Versión modular alternativa con catálogos R13/C46 + mapa ORIGEN→tipo. Misma información, agregar un modelo es 1 línea. |
| `validacion_paridad_minimo_vs_modular.sql` | `EXCEPT DISTINCT` cruzado para validar que A y B retornan exactamente lo mismo. |
| `svw_report_modelos_dly_respaldo.sql` | Snapshot del SQL original previo al cambio del 2026-04-29. Sirve de respaldo en caso de rollback. |

## Despliegue rápido

```bash
bq query --use_legacy_sql=false < svw_report_modelos_hist_minimo.sql
```

Una vista estándar de BQ es virtual: con `CREATE OR REPLACE VIEW` ya queda
activa; no hay que "ejecutarla" para refrescar datos.

## Validación post-despliegue

```sql
SELECT ORIGEN, COUNT(*) AS n,
       COUNT(DISTINCT BANDA_R13_CMF) AS n_R13,
       COUNT(DISTINCT BANDA_C46_CMF) AS n_C46
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.svw_report_modelos_hist`
WHERE FECHA_PROCESO BETWEEN DATE '<inicio>' AND DATE '<fin>'
GROUP BY ORIGEN ORDER BY ORIGEN;
```

Esperado: 12 filas, `n_R13 > 0` xor `n_C46 > 0` por cada ORIGEN.
