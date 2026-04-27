# Modelo SSV (Saldos Sin Vencimiento)

> **Autor:** vlandaetat
> **Fecha de creación:** 2026-04-20
> **Versión:** preliminar (migración del código heredado a la arquitectura del repo)

---

## Descripción

El **Modelo SSV** (Saldos Sin Vencimiento / Supuestos Sin Vencimiento) genera
la tabla de desarrollo de los 4 productos de No Madurez Definida (NMD) del
balance de personas, en dos vistas paralelas:

| Vista | Objetivo | Distribución de CORE | Destino |
|---|---|---|---|
| **GESTIÓN** | Reporting interno de balance tasas | Cuotas mensuales fijas de la hoja `CUOTAS_SSV` (metodología) | Interfaz modelos gestión |
| **NORMATIVA R13** | Reporte regulatorio (Circular 3.565, capítulo 13) | Curva `DISTR_CORE_SSV_R13` con cap `FACTOR_CORE_R13 · flujo_MO` | Interfaz modelos R13 |

Es **complementario a [ml_nmd](nmd.md)**: éste último aplica decay rate
exponencial sobre los mismos productos a nivel diario; SSV, en cambio, usa
cuotas discretas mensuales + una distribución R13 diseñada por metodología.

Productos cubiertos:

| Clave modelo | Sub-producto Access | Moneda | Vista R13 | Vista gestión |
|---|---|---|---|---|
| `CTA_CTE` | `CTA. CORRIENTE` | CLP | `MT_R13_CTA. CORRIENTE` | `MT_CTA. CORRIENTE` |
| `CTA_VTA` | `CTA. VISTA` | CLP | `MT_R13_CTA. VISTA` | `MT.CTA. VISTA` *(dot, quirk heredado)* |
| `AGD` | `CTA. AHORRO GIRO DIFERIDO` | CLF | `MT_R13_CTA. AHORRO` | `MT_CTA. AHORRO` |
| `AGI` | `CTA. AHORRO INCONDICIONAL` | CLF | `MT_R13_CTA. AHORRO` | `MT_CTA. AHORRO` |

## Ubicación

```
RF_Modelo_MR_SSV/
├── __init__.py
├── mr_ssv.py                       # lógica productiva
└── parametros/
    ├── parametros_mr_ssv.xlsx      # 3 hojas: FACTORES / CUOTAS_SSV / DISTR_CORE_SSV_R13
    └── parametros_mr_ssv.json      # generado con `python -m tools.excel_a_json mr_ssv`
```

Archivo de salida: `RF_Modelo_MR_SSV/mr_ssv.xlsx` (3 hojas: `DESARROLLO`, `DATOS`, `RESUMEN_HIST`).

## Inputs

### De sistema

| Fuente | Path | Consumo |
|---|---|---|
| MS Access | `\\vmdvorak\...\RF_Base_Carteras_Completa.accdb` → tabla `RF_BD_Gestion_RL` | Balance diario; filtro por `Fec_Pro` + 4 sub-productos. Vía cache parquet compartido con NMD/LC. |
| Excel red | `\\vmdvorak\...\Precios de Transferencia\saldos_core.xlsx` hoja `CORE_VIGENTE` | Monto CORE vigente por producto (compartido con NMD). |

### De parámetros (locales, versionados)

- **`FACTORES`** — escalares del modelo. Actualmente:
  - `FACTOR_CORE_R13 = 0.70` (cap de la vista R13).
- **`CUOTAS_SSV`** — cuotas mensuales de la vista GESTIÓN, una fila por
  (producto × cuota). Columnas: `COD_SUB_PRO_MODELO, MONEDA, N_CUOTA,
  FECHA_VENCIMIENTO_CUOTA, AMORTIZACION, FECHA_ACTUALIZACION`. **Las fechas
  están hardcodeadas por metodología** (p. ej. 42 cuotas para `CTA_CTE`
  desde 2025-10-31 hasta 2029-03-31).
- **`DISTR_CORE_SSV_R13`** — distribución normativa del CORE en fin de mes,
  una fila por (producto × cuota). Columnas: `COD_SUB_PRO_MODELO, N_CUOTA,
  DISTR_CORE_R13`. Debe sumar 1 por producto (validado en runtime).

## Algoritmo

Para cada producto `p ∈ {CTA_CTE, CTA_VTA, AGD, AGI}`:

1. **Agregar balance** por `COD_SUB_PRO_MODELO` → `FLUJO_MO[p]`.
2. **Partición CORE/NON_CORE**:
   - `monto_core_gestion[p] = Σ CUOTAS_SSV[p].AMORTIZACION`
   - `monto_core_r13[p] = min(FLUJO_MO[p] · FACTOR_CORE_R13, MONTO_CORE_GESTION_MO[p])`
   - `monto_non_core_gestion[p] = max(FLUJO_MO[p] − monto_core_gestion[p], 0)`
   - `monto_non_core_r13[p] = max(FLUJO_MO[p] − monto_core_r13[p], 0)`
3. **Construir 6 bloques de filas** de la tabla de desarrollo:

    **Vista GESTIÓN**:

    - **CORE** (N cuotas desde `CUOTAS_SSV`) —
      `CODIGO_PRODUCTO=COD_PRO_GESTION`,
      `CODIGO_SUBPRODUCTO=COD_SUB_PRO_GESTION`, `FECHA_VENCIMIENTO_CUOTA`
      de la hoja, `AMORTIZACION` de la hoja.
    - **NON_CORE** (1 fila a +1 día) —
      `CODIGO_PRODUCTO=COD_PRO_GESTION`,
      `CODIGO_SUBPRODUCTO=COD_SUB_PRO_NON_CORE_GESTION`.

    **Vista R13**:

    - **CORE distribuido** (N cuotas fin-de-mes a partir del mes siguiente)
      — `CODIGO_PRODUCTO=COD_PRO_R13`,
      `CODIGO_SUBPRODUCTO=COD_SUB_PRO_R13`,
      `AMORTIZACION = DISTR_CORE_R13 · monto_core_r13`.
    - **CORE agregado** (1 fila a +1 día) —
      `CODIGO_PRODUCTO = COD_SUB_PRO_R13`,
      `CODIGO_SUBPRODUCTO = COD_SUB_PRO_R13` (producto = subproducto por convención del reporte).
    - **NON_CORE bajo umbrella** (1 fila a +1 día) —
      `CODIGO_PRODUCTO=COD_PRO_R13`,
      `CODIGO_SUBPRODUCTO=COD_SUB_PRO_NON_CORE_R13`.
    - **NON_CORE agregado** (1 fila a +1 día) —
      `CODIGO_PRODUCTO = COD_SUB_PRO_NON_CORE_R13`,
      `CODIGO_SUBPRODUCTO = COD_SUB_PRO_NON_CORE_R13`.

    Las filas "agregadas" (product=subproduct) son una convención del
    sistema downstream: replican el total en una fila separada para
    facilitar pivots sobre `CODIGO_PRODUCTO`.

4. **Consolidar** los bloques en `DESARROLLO` (832 filas para 4 productos
   con las cantidades actuales de cuotas).
5. **Calcular control** (`RESUMEN_HIST`): flujo total, PMP, min/max
   fecha_pago por `CODIGO_PRODUCTO × CODIGO_SUBPRODUCTO`.

## Orquestación

- Registrado en [core/orquestador.py](../../core/orquestador.py) como
  `mr_ssv` (vuelta 2, orden 10).
- Invocación: `python main.py --fecha YYYY-MM-DD --modelos mr_ssv`
  o como parte de `--modelos segunda_vuelta`.
- Salida cargada a BigQuery con [carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py](../../carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py) → tabla `report_mr_ssv_dly`.
- Consolidación histórica con [carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py](../../carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py) → tabla `report_mr_ssv_hist`.
- Incluido en el email de control de segunda vuelta ([core/email_report.py](../../core/email_report.py) `TABLAS_SEGUNDA_VUELTA`).

## Validaciones activas (bloqueantes)

1. Balance no vacío para la fecha.
2. Los 4 productos presentes en balance, `CUOTAS_SSV`, `DISTR_CORE_SSV_R13` y `CORE_VIGENTE`.
3. `DISTR_CORE_SSV_R13` suma 1.0 ± 1e-6 por producto.

## Ejecución local

```bash
# Productivo (requiere entorno Windows con ODBC+Access)
python main.py --fecha 2025-10-06 --modelos mr_ssv

# Solo reescribir output + cargar a GCP (sin re-ejecutar)
python main.py --fecha 2025-10-06 --solo-carga-gcp mr_ssv

# Regenerar JSON de parámetros tras editar el Excel
python -m tools.excel_a_json mr_ssv
```
