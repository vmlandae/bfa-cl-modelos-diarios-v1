# tools/

Herramientas auxiliares y de soporte que NO forman parte del flujo
diario del orquestador. Usadas en mantencion, migraciones y cuadres.

## Catalogo

### Cuadre y conciliacion

- **`cuadre_v2.py`** -- Comparador generico entre tablas BigQuery
  `report_*_dly` y los archivos productivos xlsm de los 5 modelos de
  segunda vuelta (Inversiones, SSV, NMD, LC, Prepago CMR). Compara en
  tres niveles: totales, agrupado por `CODIGO_PRODUCTO/MONEDA_ORIGEN`,
  y fila a fila con tolerancia 0.005 absoluta. Maneja claves no unicas
  con ordinal `_seq`.

  ```bash
  python -m tools.cuadre_v2
  ```

  Genera `reports/cuadre_v2_{fecha}.xlsx` y `logs/cuadre_v2_{fecha}.log`.

### Carga BQ manual / parches

- **`cargar_prepago_cmr_productivo.py`** -- Parche temporal para subir el
  xlsm productivo de Prepago CMR a BigQuery con TRUNCATE. Usado mientras
  se valida en sombra la replica del notebook. Reutiliza
  `cargar_tablas_bigquery` del flujo dly.

  ```bash
  python -m tools.cargar_prepago_cmr_productivo 2026-04-24
  ```

### Migracion de parametros

- **`excel_a_json.py`** -- Convierte cada hoja de un Excel de parametros
  a JSON (orient=split). Cataloga los 10 modelos del repo. Usado tras
  cualquier edicion manual del xlsx para mantener coherencia con el JSON
  consumido por `cargador_parametros.py`.

  ```bash
  python -m tools.excel_a_json                # migra todos
  python -m tools.excel_a_json ml_lc          # uno solo
  python -m tools.excel_a_json --check        # solo verifica
  ```

### Migracion de snapshots

- **`migrar_snapshots.py`** -- Utilitario de migracion para reorganizar
  snapshots historicos.

### Precios

- **`build_precios_db.py`** -- Construye y sincroniza la base SQLite de
  precios a partir de los parquets de inversiones. Soporta roles
  reader/writer, sync por version contra la DB maestra en red, y
  exportacion CSV TCRC.

### Diagnostico

- **`check_env.py`** -- Verifica el entorno conda y dependencias
  criticas.
- **`test_gcp_permisos.py`** -- Prueba permisos GCP de la cuenta de
  servicio (lectura, escritura, eliminacion en BQ).
