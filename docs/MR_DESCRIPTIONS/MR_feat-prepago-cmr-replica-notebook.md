# feat/prepago-cmr-replica-notebook -> main

Reemplazo del modelo `mr_prepago_cmr` por una replica fiel del notebook
productivo (`Generador_Prepago_TC_CMR_Productivo.ipynb`), validada al
centavo contra el output diario; mas herramientas auxiliares de cuadre
y un parche de carga manual a BigQuery utilizado mientras se valida la
nueva implementacion.

**URL para abrir el MR:**
https://gitlab.falabella.tech/rmunozb/bfa-cl-modelos-diarios/-/merge_requests/new?merge_request%5Bsource_branch%5D=feat%2Fprepago-cmr-replica-notebook

---

## Resumen ejecutivo

- `mr_prepago_cmr.py` ahora es una traduccion 1:1 del notebook productivo,
  conectada al pipeline del repo (cache parquet, `config_rutas`,
  `guardar_excel`, snapshot historico).
- La version anterior parametrizada via Excel queda como
  `mr_prepago_cmr_dev.py` (no usada por el orquestador) para retomar las
  mejoras en una rama de desarrollo posterior.
- Nueva herramienta `tools/cuadre_v2.py`: comparador generico BQ vs xlsm
  para los 5 modelos de segunda vuelta.
- Parche temporal `tools/cargar_prepago_cmr_productivo.py` para subir el
  xlsm productivo a BigQuery con TRUNCATE mientras se confirma la
  validacion en sombra.
- Documento de hallazgos
  (`docs/feats/cuadre-mr-prepago-cmr/hallazgos.md`) con el analisis
  comparativo, hipotesis y caminos posibles para discutir con
  metodologias.
- Refresh de parametros productivos `ml_lc` (xlsx + regeneracion del
  json) -- cambio rutinario incluido en el MR.

## Validacion

Ejecutado para fecha 2026-04-24:

| Metrica | PROD (notebook) | DEV (mr_prepago_cmr.py) | Diff |
|---|---|---|---|
| Filas hoja DESARROLLO | 2.697 | 2.697 | 0 |
| AMORTIZACION total | 5.054.057.879.737 | 5.054.057.879.737 | 0,0000 |
| INTERES total | 1.280.547.531.180 | 1.280.547.531.180 | 0,0000 |

Cuadre exacto a nivel `CODIGO_PRODUCTO` x `CODIGO_SUBPRODUCTO` (6 grupos
BASE/UP/DOWN x SAV/NO_SAV).

## Cambios por area

### Modelo Prepago CMR (`RF_Modelo_Prepago_CMR/`)
- `mr_prepago_cmr.py` reemplazado por replica fiel del notebook.
  Comportamiento clave: `Dia_F.replace({28:30, 29:30})` siempre, MORA con
  vencimiento pasado en NO_SAV, calendario directo sin vector 200 meses,
  `SMM/100`, escenarios hardcoded `[1.0, 0.8, 1.2]`, `CODIGO_EMPRESA = 3`.
- `mr_prepago_cmr_dev.py` (nuevo): version parametrizada anterior
  preservada para iteracion futura. Banner explicito en el docstring.
- Mantiene la firma `ejecutar_modelo(fecha) -> bool` del orquestador.

### Tools (`tools/`)
- `cuadre_v2.py`: comparador BQ vs xlsm (3 niveles: totales, por
  CODIGO_PRODUCTO/MONEDA, fila a fila con tolerancia 0.005). Maneja
  duplicados con ordinal `_seq`, normaliza dbdate de BQ y castea claves
  string. Generico para los 5 modelos de segunda vuelta.
- `cargar_prepago_cmr_productivo.py`: parche manual de carga a BQ con
  TRUNCATE. Reusa `cargar_tablas_bigquery` del flujo dly.
- `README.md` (nuevo): catalogo de las herramientas auxiliares del repo.

### Carga BigQuery (`carga_modelos_gcp/`)
- `cargar_output_modelos_bigquery_dly.py`: emojis (`tick`, `cruz`)
  reemplazados por texto plano `OK`/`ERROR` para evitar
  `UnicodeEncodeError` cuando stdout es cp1252 (Windows).

### Parametros LC (`RF_Modelo_Linea_de_Credito/parametros/`)
- `parametros_ml_lc.xlsx`: refresh rutinario de valores productivos.
- `parametros_ml_lc.json`: regenerado desde el xlsx con
  `python -m tools.excel_a_json ml_lc` para mantener coherencia entre
  ambos formatos.

### Documentacion
- `docs/CHANGELOG.md`: entrada
  `[1.14.0-dev] - 2026-04-27 - Prepago CMR replica notebook + cuadre`.
- `docs/feats/cuadre-mr-prepago-cmr/hallazgos.md`: analisis comparativo
  notebook vs implementacion anterior, 5 divergencias funcionales, 6
  hipotesis ordenadas y 4 caminos posibles.

## Pendientes / siguientes pasos

- Validar en sombra durante varios dias antes de cerrar el parche manual
  (`tools/cargar_prepago_cmr_productivo.py`).
- Discutir con metodologias las hipotesis del documento de hallazgos
  (especialmente unidad SMM en parametros y `CODIGO_EMPRESA = 3 vs 1`).
- Definir si las mejoras de la version dev (parametrizacion via Excel,
  escenarios desde config) se reincorporan en una rama futura o si se
  descartan.

## Notas

- Sin emojis ni caracteres no-ASCII en los archivos `.py` y `.yaml`
  (regla repo Windows cp1252).
- Todos los `open()` con `encoding='utf-8'`.
- El modelo dev_v0 fue desarrollado, validado y promovido a productivo
  en una sola sesion -- la conversacion completa quedo registrada en el
  doc de hallazgos.
