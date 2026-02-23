# Creación y Verificación de Tablas BigQuery — Modelo Inversiones

Documento de auditoría que registra los pasos exactos ejecutados para crear las
tablas de BigQuery del modelo de inversiones, las pruebas realizadas y sus
resultados.

**Fecha de ejecución:** 2026-02-23  
**Ejecutado por:** vlandaetat (asistido por GitHub Copilot)  
**Branch:** `feat/modelo-inversiones`  
**Entorno:** conda `bfa-cl-modelos`, Windows 11  
**Proyecto GCP:** `bfa-cl-trade-price-report-dev`  
**Credenciales:** `credenciales/bfa-cl-trade-price-report-dev-9d137fc23b7f.json`

---

## 1. Tabla Daily — `report_ml_inversiones_dly`

### 1.1 Creación

La tabla daily **no se creó manualmente**. Fue creada automáticamente por
`bfa_cl_utilidades.cargar_dataframe_bigquery()` con `tipo_escritura="TRUNCATE"`
(`WRITE_TRUNCATE`), que crea la tabla si no existe usando el esquema pasado por
parámetro (`crear_esquema_base()`).

- **Dataset:** `bfa_cl_prd_financial_risk_dly_proc_models`
- **Tabla:** `report_ml_inversiones_dly`
- **Referencia completa:** `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.report_ml_inversiones_dly`

### 1.2 Esquema (32 columnas)

Definido en `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py` →
función `crear_esquema_base()`:

| Campo | Tipo | Modo |
|---|---|---|
| FECHA_PROCESO | DATE | REQUIRED |
| CODIGO_EMPRESA | INTEGER | NULLABLE |
| OPERACION | INTEGER | NULLABLE |
| COD_ACT_PAS | STRING | NULLABLE |
| MONEDA_ORIGEN | STRING | NULLABLE |
| MONEDA_COMPENSACION | STRING | NULLABLE |
| COMPENSACION | INTEGER | NULLABLE |
| CODIGO_PRODUCTO | STRING | REQUIRED |
| CODIGO_SUBPRODUCTO | STRING | REQUIRED |
| FECHA_CREACION | DATE | NULLABLE |
| NUMERO_CUOTA | INTEGER | NULLABLE |
| FECHA_INICIO_CUOTA | DATE | NULLABLE |
| FECHA_VENCIMIENTO_CUOTA | DATE | NULLABLE |
| FECHA_PAGO | DATE | NULLABLE |
| FECHA_REPRICING | DATE | NULLABLE |
| AMORTIZACION | FLOAT | NULLABLE |
| INTERES | FLOAT | NULLABLE |
| INTERES_DEVENGADO | FLOAT | NULLABLE |
| VP_AMORTIZACION | FLOAT | NULLABLE |
| VP_INTERES | FLOAT | NULLABLE |
| FACTOR_DE_RIESGO | STRING | NULLABLE |
| TIPO_CUOTA | INTEGER | NULLABLE |
| AREA_NEGOCIO | STRING | NULLABLE |
| CODIGO_EJECUTIVO | STRING | NULLABLE |
| CODIGO_ESTRATEGIA | STRING | NULLABLE |
| CLASIFICACION_CONTABLE | STRING | NULLABLE |
| TIPO_TASA | INTEGER | NULLABLE |
| INDEXADOR | STRING | NULLABLE |
| TASA | FLOAT | NULLABLE |
| TASA_CF | FLOAT | NULLABLE |
| SPREAD | FLOAT | NULLABLE |
| FECHA_ACTUALIZACION | DATETIME | NULLABLE |

### 1.3 Carga de prueba

**Script usado:** `tmpclaude-gcp-test.py` (eliminado tras documentación)

```python
# Llamada efectiva que creó y pobló la tabla:
from carga_modelos_gcp.cargar_output_modelos_bigquery_dly import (
    cargar_tablas_bigquery, crear_esquema_base
)

resultado = cargar_tablas_bigquery(
    fecha_t=datetime.datetime(2026, 2, 20),
    ruta_archivo=Path("RF_Modelo_Inversiones/ml_inversiones.xlsx"),
    hoja_archivo="INTERFAZ_MODELO_INVERSIONES",
    tabla_respaldo="report_ml_inversiones_dly",
    esquema_tabla=crear_esquema_base(),
    tipo_carga="TRUNCATE"
)
```

**Resultado completo del log de ejecución:**

```
1. Importando modulos...
2. Modulos importados OK
3. Ruta: RF_Modelo_Inversiones\ml_inversiones.xlsx, existe: True
[33272] Iniciando carga de: RF_Modelo_Inversiones\ml_inversiones.xlsx
        (hoja: INTERFAZ_MODELO_INVERSIONES) para la fecha: 2026-02-20
Datos cargados exitosamente en
  'bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.report_ml_inversiones_dly'
Filas procesadas: 837
4. Resultado: [33272] Carga exitosa: report_ml_inversiones_dly
EXIT=0
```

### 1.4 Verificación post-carga

**Script usado:** `tmpclaude-verify-bq.py` (eliminado tras documentación)

```python
# Verificación:
from google.cloud import bigquery
client = bigquery.Client.from_service_account_json(
    'credenciales/bfa-cl-trade-price-report-dev-9d137fc23b7f.json',
    project='bfa-cl-trade-price-report-dev')

t = client.get_table(
    'bfa-cl-trade-price-report-dev'
    '.bfa_cl_prd_financial_risk_dly_proc_models'
    '.report_ml_inversiones_dly')

q = client.query(
    'SELECT FECHA_PROCESO, COUNT(*) cnt '
    'FROM bfa_cl_prd_financial_risk_dly_proc_models.report_ml_inversiones_dly '
    'GROUP BY 1')
```

**Resultado de la verificación:**

```
Tabla: report_ml_inversiones_dly
Filas: 837
Columnas: 32
Fecha: 2026-02-20, count: 837
VERIFY OK
```

---

## 2. Tabla Histórica — `report_ml_inversiones_hist`

### 2.1 Creación

La tabla histórica **sí fue creada manualmente** con DDL porque el proceso de
consolidación (`consolidar_historico_bigquery`) usa `INSERT INTO` y requiere
que la tabla destino ya exista.

**Script usado:** `tmpclaude-create-hist.py` (eliminado tras documentación)

**DDL ejecutado vía `bfa_cl_utilidades.ejecutar_query_bigquery()`:**

```sql
CREATE TABLE IF NOT EXISTS
  `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_inversiones_hist`
(
  FECHA_PROCESO DATE NOT NULL,
  CODIGO_EMPRESA INT64,
  OPERACION INT64,
  COD_ACT_PAS STRING,
  MONEDA_ORIGEN STRING,
  MONEDA_COMPENSACION STRING,
  COMPENSACION INT64,
  CODIGO_PRODUCTO STRING NOT NULL,
  CODIGO_SUBPRODUCTO STRING NOT NULL,
  FECHA_CREACION DATE,
  NUMERO_CUOTA INT64,
  FECHA_INICIO_CUOTA DATE,
  FECHA_VENCIMIENTO_CUOTA DATE,
  FECHA_PAGO DATE,
  FECHA_REPRICING DATE,
  AMORTIZACION FLOAT64,
  INTERES FLOAT64,
  INTERES_DEVENGADO FLOAT64,
  VP_AMORTIZACION FLOAT64,
  VP_INTERES FLOAT64,
  FACTOR_DE_RIESGO STRING,
  TIPO_CUOTA INT64,
  AREA_NEGOCIO STRING,
  CODIGO_EJECUTIVO STRING,
  CODIGO_ESTRATEGIA STRING,
  CLASIFICACION_CONTABLE STRING,
  TIPO_TASA INT64,
  INDEXADOR STRING,
  TASA FLOAT64,
  TASA_CF FLOAT64,
  SPREAD FLOAT64,
  FECHA_ACTUALIZACION DATETIME
)
PARTITION BY FECHA_PROCESO
OPTIONS(
  description='Tabla historica modelo inversiones'
);
```

**Código Python equivalente:**

```python
import bfa_cl_utilidades as ut
from config import config_rutas as cr

ruta = str(cr.obtener_ruta_credenciales_gcp())
result = ut.ejecutar_query_bigquery(ruta, ddl)  # ddl = la consulta SQL de arriba
```

**Resultado:**

```
OK: report_ml_inversiones_hist, 32 cols
EXIT=0
```

- **Dataset:** `bfa_cl_prd_financial_risk_dly_proc_models_hist`
- **Tabla:** `report_ml_inversiones_hist`
- **Partición:** `FECHA_PROCESO` (DATE)
- **Referencia completa:** `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_inversiones_hist`

### 2.2 Consolidación de prueba (daily → hist)

**Script usado:** `tmpclaude-hist-test.py` (eliminado tras documentación)

```python
from carga_modelos_gcp.cargar_output_modelos_bigquery_hist import (
    consolidar_historico_bigquery
)

resultados = consolidar_historico_bigquery(
    datetime.datetime(2026, 2, 20),
    modelos_a_consolidar=['ml_inversiones']
)
```

La función `consolidar_historico_bigquery` ejecuta internamente:

```sql
INSERT INTO `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models_hist.report_ml_inversiones_hist`
SELECT *
FROM `bfa-cl-trade-price-report-dev.bfa_cl_prd_financial_risk_dly_proc_models.report_ml_inversiones_dly`
WHERE DATE(FECHA_PROCESO) = DATE('2026-02-20');
```

**Resultado completo:**

```
CONSOLIDACION HISTORICA EN BIGQUERY
Fecha de proceso: 20-02-2026
Total de tablas a consolidar: 1

--- Procesando bfa_cl_prd_financial_risk_dly_proc_models.report_ml_inversiones_dly
    para la fecha: 2026-02-20 ---
1. Verificando si ya existen datos en report_ml_inversiones_hist
   para la fecha 2026-02-20...
   No hay datos existentes. Procediendo con la inserción...
2. Insertando datos en report_ml_inversiones_hist...
   Registros insertados: 837
--- report_ml_inversiones_dly Terminado ---

CONSOLIDACION FINALIZADA
Exitosos: 1/1
report_ml_inversiones_hist: OK
EXIT=0
```

---

## 3. Dry-run — Validación del pipeline de columnas

### 3.1 Problema detectado y resuelto

El Excel generado por `ml_inversiones.py` usa nombres de columnas con
**espacios** (ej. `FECHA PROCESO`, `AREA NEGOCIO`, `TASA CF`), mientras que
el esquema BQ y los otros modelos usan guiones bajos (`FECHA_PROCESO`,
`AREA_NEGOCIO`, `TASA_CF`).

Además, el campo `COMPENSACION` contiene el string `"C"` (no un entero) y
campos como `OPERACION`, `NUMERO_CUOTA`, `TASA`, `SPREAD` contienen cadenas
vacías `""` que no se pueden convertir a `Int64`/`float`.

### 3.2 Solución implementada en `cargar_output_modelos_bigquery_dly.py`

1. **Peek-based detection:** Lee `nrows=0` del Excel para ver si las columnas
   tienen espacios.
2. **Normalización condicional:** Si detecta columnas con espacios, lee sin
   `dtype` forzado, renombra con `_normalizacion_cols`, luego hace
   `df.replace('', np.nan)` y recastea con `pd.to_numeric(errors='coerce')`
   para los tipos numéricos.
3. **Conversión de fechas robusta:** Cambiado de `format='%Y-%m-%d %H:%M:%S'`
   a `format='mixed'` para manejar tanto datetime nativos de openpyxl como
   strings de otros modelos.
4. Si **no** necesita normalización (todos los otros modelos), usa el path
   original: `pd.read_excel(..., dtype=dtype_excel)`.

### 3.3 Resultado del dry-run

**Script usado:** `tmpclaude-dryrun.py` (eliminado tras documentación)

```
Necesita normalización: True
Columnas renombradas: ['FECHA PROCESO', 'FECHA CREACION', 'FECHA PAGO',
  'FACTOR DE RIESGO', 'AREA NEGOCIO', 'CODIGO_ EJECUTIVO', 'TIPO TASA',
  'TASA CF', 'COD ACT/PAS']

Columnas FINALES (32):
  FECHA_PROCESO: object        CODIGO_EMPRESA: int64
  OPERACION: float64           COD_ACT_PAS: object
  MONEDA_ORIGEN: object        MONEDA_COMPENSACION: object
  COMPENSACION: float64        CODIGO_PRODUCTO: object
  CODIGO_SUBPRODUCTO: object   FECHA_CREACION: datetime64[ns]
  NUMERO_CUOTA: float64        FECHA_INICIO_CUOTA: datetime64[ns]
  FECHA_VENCIMIENTO_CUOTA: object   FECHA_PAGO: object
  FECHA_REPRICING: object      AMORTIZACION: float64
  INTERES: float64             INTERES_DEVENGADO: int64
  VP_AMORTIZACION: float64     VP_INTERES: float64
  FACTOR_DE_RIESGO: object     TIPO_CUOTA: int64
  AREA_NEGOCIO: object         CODIGO_EJECUTIVO: object
  CODIGO_ESTRATEGIA: object    CLASIFICACION_CONTABLE: object
  TIPO_TASA: int64             INDEXADOR: object
  TASA: float64                TASA_CF: float64
  SPREAD: float64              FECHA_ACTUALIZACION: datetime64[us]

Filas: 837
Todas las columnas coinciden con el esquema BQ
```

---

## 4. Mapeo de normalización de columnas

| Columna en Excel (ml_inversiones) | Columna en BQ / otros modelos |
|---|---|
| `FECHA PROCESO` | `FECHA_PROCESO` |
| `FECHA CREACION` | `FECHA_CREACION` |
| `FECHA PAGO` | `FECHA_PAGO` |
| `FACTOR DE RIESGO` | `FACTOR_DE_RIESGO` |
| `AREA NEGOCIO` | `AREA_NEGOCIO` |
| `CODIGO_ EJECUTIVO` | `CODIGO_EJECUTIVO` |
| `TIPO TASA` | `TIPO_TASA` |
| `TASA CF` | `TASA_CF` |
| `COD ACT/PAS` | `COD_ACT/PAS` → `COD_ACT_PAS` |

> Nota: `CODIGO_ EJECUTIVO` tiene un espacio extra después del guion bajo en
> el Excel original. Esto es intencional y coincide con lo que genera
> `tabla_final.py`.

---

## 5. Archivos temporales eliminados

Todos los scripts y logs listados a continuación fueron creados exclusivamente
para pruebas de integración y eliminados tras documentar sus resultados aquí:

| Archivo | Propósito |
|---|---|
| `tmpclaude-dryrun.py` | Simular pipeline de lectura+rename+dtype sin escribir a BQ |
| `tmpclaude-dryrun-result.log` | Output del dry-run |
| `tmpclaude-gcp-test.py` | Ejecutar `cargar_tablas_bigquery()` para daily upload |
| `tmpclaude-gcp-result.log` | Log de la carga daily |
| `tmpclaude-verify-bq.py` | Verificar schema y filas en BQ post-carga |
| `tmpclaude-bq-verify.log` | Output de la verificación |
| `tmpclaude-create-hist.py` | Crear tabla histórica con DDL |
| `tmpclaude-create-hist.log` | Confirmación de creación |
| `tmpclaude-hist-test.py` | Ejecutar consolidación daily→hist |
| `tmpclaude-hist-result.log` | Log de la consolidación |
| `tmpclaude-debug-cols.py` | Inspeccionar dtypes y valores 'C' en columnas |
| `tmpclaude-run-gcp.sh` | Wrapper bash con `trap '' INT` para evitar Ctrl-C |

---

## 6. Resumen de estado final

| Tabla | Dataset | Filas | Fecha | Estado |
|---|---|---|---|---|
| `report_ml_inversiones_dly` | `bfa_cl_prd_financial_risk_dly_proc_models` | 837 | 2026-02-20 | OK |
| `report_ml_inversiones_hist` | `bfa_cl_prd_financial_risk_dly_proc_models_hist` | 837 | 2026-02-20 | OK |
