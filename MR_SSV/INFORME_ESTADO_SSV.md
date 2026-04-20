# Informe de estado — Modelo SSV (MR_SSV)

Rama: `feat/modelo-ssv`
Fecha informe: 2026-04-20
Fuente: `MR_SSV.zip` descomprimido en `MR_SSV/`

---

## 1. ¿Qué es el modelo SSV?

El modelo **SSV** (Saldos Sin Vencimiento / Supuestos Sin Vencimiento) genera la tabla de desarrollo de los **productos de No Madurez Definida (NMD)** bajo dos vistas:

- **Vista GESTIÓN**: reparte el flujo en una porción `CORE` (con cuotas dadas por metodología, hoja `CUOTAS_SSV`) más una porción `NON_CORE` que vence al día siguiente.
- **Vista NORMATIVA R13**: reparte el flujo en `CORE_R13` (=`min(flujo·0.70, core_gestión)`) distribuido por la curva `DISTR_CORE_SSV_R13`, más `NON_CORE_R13` y dos filas auxiliares de agregado normativo.

Productos cubiertos (cuatro): `CTA_CTE` (CLP), `CTA_VTA` (CLP), `AGD` (CLF) y `AGI` (CLF). **No cubre DAP** (eso lo hace `ml_nmd`).

En la práctica es un **modelo complementario a `ml_nmd`**: mientras `ml_nmd` entrega la vista de **gestión con decay rate exponencial** (series diarias 1.095 días) para estos mismos productos, **SSV entrega la vista con cuotas mensuales discretas y la vista normativa R13**. Ambos consumen `RF_BD_Gestion_RL` (Access) y `saldos_core.xlsx` (red).

## 2. Contenido del zip descomprimido

| Ruta | Tipo | Descripción |
|---|---|---|
| [MR_SSV/mr_ssv.py](MR_SSV/mr_ssv.py) | Código | Script monolítico del modelo (516 líneas). Patrón *viejo* con `HERRAMIENTAS/utilidades_bfal`, rutas UNC hardcodeadas y macros Excel. |
| [MR_SSV/parametros_ssv.xlsx](MR_SSV/parametros_ssv.xlsx) | Parámetros | 2 hojas: `CUOTAS_SSV` (494 filas — 4 productos × 42 a 205 cuotas) y `DISTR_CORE_SSV_R13` (322 filas — distribuciones que suman 1 por producto). |
| [MR_SSV/mt_ssv_local_cc.XLSM](MR_SSV/mt_ssv_local_cc.XLSM) | Output base | Plantilla **con macros VBA**: `control_y_correo_diario`, `actualiza_dinamica_control`, `enviar_correo_Outlook`, `control_comparacion_dia`. 4 hojas: `DESARROLLO`, `DATOS`, `CONTROL` (tabla dinámica), `RESUMEN_HIST`. |
| MR_SSV/OTROS/* | Históricos | Versiones previas del XLSM (sept/oct 2025). No se usan. |

Parámetros clave observados:
- **FACTOR_CORE_R13 = 0.70** hardcodeado en [MR_SSV/mr_ssv.py:53](MR_SSV/mr_ssv.py#L53)
- Fecha de actualización de `CUOTAS_SSV`: 2025-10-01 → **los cuadros de cuotas están vigentes a esa fecha**; habrá que refrescarlos periódicamente.

## 3. Análisis del código actual

### 3.1 Flujo del script ([MR_SSV/mr_ssv.py](MR_SSV/mr_ssv.py))

1. `cargar_datos_balance()` — SQL directo a `RF_BD_Gestion_RL` (Access UNC) filtrando DAP, Cta Cte, Cta Vista, Cta Ahorro y Línea de Crédito. **Nota**: trae Línea de Crédito pero luego no la usa.
2. `cargar_parametros_modelo()` — lee `parametros_ssv.xlsx` (2 hojas) + `saldos_core.xlsx` hoja `CORE_VIGENTE`.
3. `procesar_modelo()`:
   - Mapea `COD_SUB_PRO` → `CTA_VTA|CTA_CTE|AGD|AGI`.
   - Merge con `MONTO_CORE_GESTION_MO` del core vigente.
   - `MONTO_CORE_R13 = min(FLUJO·0.70, MONTO_CORE_GESTION)`.
   - **Loop por producto** (no vectorizado) que arma `tabla_desarrollo_gestion` y `tabla_desarrollo_r13` con los dicts de filas.
4. Escribe 3 hojas del XLSM con `ut.cargar_datos_xlsm`: `DESARROLLO`, `RESUMEN_HIST`, `DATOS`.
5. Dispara macro VBA `control_y_correo_diario`.

### 3.2 Deuda técnica respecto al estándar del repo

El código está **en el patrón heredado de otro repositorio** (`HERRAMIENTAS/utilidades_bfal`, rutas UNC absolutas, macros VBA, ejecución COM). No está integrado a la arquitectura actual:

| Aspecto | Estado en `mr_ssv.py` | Estándar en el repo |
|---|---|---|
| Imports utilidades | `import HERRAMIENTAS.utilidades_bfal as ut` (busca carpeta ascendente) | `import bfa_cl_utilidades as ut` + `from config import config_rutas as cr` |
| Rutas externas | Constantes hardcodeadas (`r"\\vmdvorak\..."`) | `config/config_rutas_ext_y_archivos.yaml` + `cr.resolver_ruta(...)` |
| Lectura Access | `ut.lectura_datos_ms_access(...)` directo | `procesamiento_datos_input.cache_tablas.leer_tabla_con_cache` (parquet compartido con NMD/LC) |
| Parámetros | Lee `.xlsx` directo | `cargador_parametros.cargar_hojas_parametros("mr_ssv")` (JSON preferido, Excel fallback, validación con caché) |
| Output | `.XLSM` con macros y `pythoncom` | `.xlsx` plano vía `core.excel_output.guardar_excel` (xlsxwriter) |
| Firma de ejecución | `procesar_modelo(fecha_proceso) -> None` invocado vía `sys.argv[1]` | `ejecutar_modelo(fecha_proceso: datetime) -> bool` |
| Orquestación | Stand-alone `python mr_ssv.py YYYY-MM-DD` | `core.orquestador.OrquestadorModelos` registra el modelo y lo ejecuta en la “segunda vuelta” |
| Carga a BigQuery | Ninguna | Tabla `report_mr_ssv_dly` en `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py` + histórica |
| Reporte email / control | Macro `control_y_correo_diario` en Excel | `core.email_report` + `core.control_interfaces` en Python |
| Preflight / snapshot | Ninguno | `core.preflight` + snapshot content-addressable automático |
| Logging | `print(...)` | `core.logger.get_logger(__name__)` |

### 3.3 Bugs o *smells* detectados en la lógica

- **L83-90**: el `HAVING` con `OR` sin paréntesis provoca que `Cod_Sub_Pro='DAP'` exija `AND`, mientras el resto queda en OR. La lógica queda fraccionada y trae `DAP` y `LINEA DE CREDITO` que luego no se usan.
- **L278**: referencia comentada a `"COD_SUB_PRO"` cuando la columna real es `COD_SUB_PRO_MODELO`.
- **L339**: `"CODIGO_PRODUCTO": [p_codigos_productos[i]["COD_SUB_PRO_NON_CORE_R13"]]` — usa `COD_SUB_PRO_*` como `CODIGO_PRODUCTO`. Esto coincide con lo que efectivamente quedó en la plantilla XLSM (`MT_R13_CTA. VISTA_NONCORE` aparece como producto *y* subproducto), pero conviene validar con metodología si es intencional o un artefacto.
- **Rendimiento**: el doble loop (`for i in COD_SUB_PRO_MODELO` y `for j in range(1, cuotas_r13+1)` construyendo fechas día a día con `concat` dentro del loop) es O(n²) en `DataFrame.concat`. Con ~550 filas totales no duele, pero conviene vectorizar al migrar.
- `FACTOR_CORE_R13 = 0.70` hardcodeado — debería migrar al archivo de parámetros.

## 4. Checklist para productivizar

### 4.1 Estructura de archivos (crear)

- [ ] Carpeta `RF_Modelo_MR_SSV/` (convención del resto del repo) con:
  - [ ] `__init__.py`
  - [ ] `mr_ssv.py` reescrito (ver §4.3)
  - [ ] `parametros/parametros_mr_ssv.xlsx` (copia del actual `parametros_ssv.xlsx`)
  - [ ] `parametros/parametros_mr_ssv.json` generado con `python -m tools.excel_a_json mr_ssv`
  - [ ] `mr_ssv.xlsx` (output plano, ver §4.4)
- [ ] Eliminar `MR_SSV.zip` del repo una vez movido el contenido.

### 4.2 Configuración central

- [ ] [config/config_rutas_ext_y_archivos.yaml](config/config_rutas_ext_y_archivos.yaml) — nuevo bloque:

  ```yaml
  mr_ssv:
    ms_access_input: "\\\\vmdvorak\\Riesgo Financiero2\\RF_PROCESOS\\RF_Carteras\\INTERFAZ_DATOS\\RF_Base_Carteras_Completa.accdb"
    ms_access_tabla_input: "RF_BD_Gestion_RL"
    excel_parametros_modelo_input: "RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.xlsx"
    excel_parametros_core_input: "\\\\vmdvorak\\Riesgo Financiero2\\RF_PROCESOS\\RF_Resultados\\Precios de Transferencia\\saldos_core.xlsx"
    excel_output: "RF_Modelo_MR_SSV/mr_ssv.xlsx"
  ```

- [ ] [procesamiento_datos_input/cargador_parametros.py:41](procesamiento_datos_input/cargador_parametros.py#L41) — agregar `"mr_ssv": "RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.xlsx"` en `_CATALOGO`.
- [ ] [core/orquestador.py:23](core/orquestador.py#L23) — registrar el modelo. Dado que comparte fuente Access con `ml_nmd` y `ml_lc`, lo natural es dejarlo en **vuelta 2**:

  ```python
  "mr_ssv": {
      "nombre": "Modelo SSV (Saldos Sin Vencimiento)",
      "modulo": "RF_Modelo_MR_SSV.mr_ssv",
      "activado": True, "orden": 10, "vuelta": 2,
      "tiene_carga_gcp": True, "tiene_carga_gcp_historica": True,
  }
  ```

- [ ] [main.py:61](main.py#L61) — agregar `'mr_ssv': ['report_mr_ssv_dly']` en `MODELO_A_TABLAS`.

### 4.3 Reescritura de `mr_ssv.py` (plantilla sugerida)

- [ ] Reemplazar header `HERRAMIENTAS.utilidades_bfal` por el patrón de [RF_Modelo_NMD/ml_nmd.py:1-22](RF_Modelo_NMD/ml_nmd.py#L1-L22):
  - `import bfa_cl_utilidades as ut`
  - `from config import config_rutas as cr`
  - `from core.excel_output import guardar_excel`
  - Leer rutas desde `config_ext['modelos']['mr_ssv']`.
- [ ] `cargar_datos_balance(fecha_t)` — usar `leer_tabla_con_cache` (aprovecha el parquet que ya deja `ml_nmd` en la misma vuelta). Filtro reducido a los 4 productos reales: `CTA. CORRIENTE`, `CTA. VISTA`, `CTA. AHORRO GIRO DIFERIDO`, `CTA. AHORRO INCONDICIONAL`. Filtrar por `Fec_Pro = fecha_t`.
- [ ] `cargar_parametros()` — usar `cargar_hojas_parametros("mr_ssv")` para las 2 hojas (`CUOTAS_SSV`, `DISTR_CORE_SSV_R13`) y `pd.read_excel(RUTA_PARAMETROS_CORE, sheet_name="CORE_VIGENTE")` con el mismo patrón que NMD.
- [ ] Mover `FACTOR_CORE_R13` (0.70) a una nueva hoja `FACTORES` del parámetro, o a `config_rutas_ext_y_archivos.yaml` bajo `mr_ssv.parametros.factor_core_r13`.
- [ ] Estructurar la función pública como:

  ```python
  def ejecutar_modelo(fecha_proceso: datetime) -> bool:
      ...
      guardar_excel(ruta_archivo=RUTA_OUTPUT_MODELO,
                    hojas={"DESARROLLO": df_desarrollo,
                           "DATOS": df_datos,
                           "RESUMEN_HIST": df_resumen})
      return True
  ```

- [ ] Reemplazar el doble loop por construcción vectorizada (`pd.concat([...]).assign(...)` por producto) o, como mínimo, acumular en listas y hacer un único `pd.concat` al final.
- [ ] Borrar todo el bloque `pythoncom` + `ejecutar_macro_excel`. El control diario pasa a `core.email_report` / `core.control_interfaces`.
- [ ] Agregar `validar_datos_iniciales(...)` al estilo [RF_Modelo_NMD/ml_nmd.py:514](RF_Modelo_NMD/ml_nmd.py#L514) (chequea filas positivas, 4 productos presentes, cuotas en parámetros, suma de `DISTR_CORE_R13` ≈ 1 por producto).
- [ ] Logging con `get_logger(__name__)` (no `print`).

### 4.4 Migración XLSM → XLSX

- [ ] Confirmar con metodología si las hojas `CONTROL` (tabla dinámica) y las macros VBA (`control_y_correo_diario`, `actualiza_dinamica_control`, `enviar_correo_Outlook`, `control_comparacion_dia`) son **requeridas** por el cliente final o son *controles internos*.
  - Si son internos → descartar el XLSM y dejar sólo `mr_ssv.xlsx` con hojas `DESARROLLO`, `DATOS`, `RESUMEN_HIST`; portar el correo a [core/email_report.py](core/email_report.py) y el control a [core/control_interfaces.py](core/control_interfaces.py) con un bloque `mr_ssv:` en `config_rutas_ext_y_archivos.yaml`.
  - Si la macro es obligatoria (p. ej. envío vía Outlook desde una estación Windows) → dejar el XLSM como output secundario pero replicar el correo en Python igual, para poder correr en el orquestador automático.

### 4.5 Carga a BigQuery

- [ ] [carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py:276](carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py#L276) — agregar tarea:

  ```python
  'mr_ssv': {
      'fecha_t': fecha_proceso,
      'ruta_archivo': Path(config_ext['modelos']['mr_ssv']['excel_output']),
      'hoja_archivo': "DESARROLLO",
      'tabla_respaldo': "report_mr_ssv_dly",
      'esquema_tabla': crear_esquema_base(),
      'tipo_carga': "TRUNCATE",
      'modelo_origen': 'mr_ssv',
  }
  ```

- [ ] Hacer lo equivalente en `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` (tabla histórica `report_mr_ssv_hist`).
- [ ] Validar que el esquema base cubre todas las columnas del DESARROLLO (lo hace — ya lo comparten NMD y LC).

### 4.6 Consideraciones de datos / metodología

- [ ] Refresco de parámetros `CUOTAS_SSV` y `DISTR_CORE_SSV_R13`: hoy están fechados al 2025-10-01. Definir cadencia (¿mensual? ¿trimestral?) y responsable. El orquestador hace snapshot automático del Excel/JSON cada día, así que queda trazabilidad.
- [ ] Unificar con `ml_nmd`: ambos leen `saldos_core.xlsx` y `RF_BD_Gestion_RL` para los mismos 4 productos. El parquet compartido ya lo resuelve en runtime, pero conviene dejar documentado que si se cambia el mapeo de productos en uno debe cambiarse en el otro.
- [ ] Validar si los `CODIGO_PRODUCTO` que terminan iguales al `CODIGO_SUBPRODUCTO` (filas auxiliares R13, ver §3.3) están así por diseño o es un bug heredado.

### 4.7 Documentación y tests

- [ ] Crear [docs/modelos/ssv.md](docs/modelos/ssv.md) con metodología, diagrama de flujo y ejemplo de corrida — al estilo de los otros modelos del folder.
- [ ] Smoke test: ejecución con fecha conocida (2025-09-30 o 2025-10-06) que produzca output y lo cargue a una tabla `report_mr_ssv_dly_test` antes de habilitar la carga oficial.
- [ ] Agregar el modelo a los reportes de `primera_vuelta/segunda_vuelta` en [core/email_report.py](core/email_report.py) si aplica.

## 5. Resumen ejecutivo

**Lo que tenemos** (en el zip):

- Lógica de negocio **completa y auto-contenida** del modelo SSV (4 productos NMD × 2 vistas).
- Parámetros actualizados a 2025-10-01.
- Plantilla XLSM con macros que hoy envían el control diario por Outlook.

**Lo que falta** (para productivizar):

1. **Mover** el código al patrón del repo (`config`, `cache_tablas`, `cargador_parametros`, `excel_output`, `logger`, firma `ejecutar_modelo -> bool`).
2. **Registrar** el modelo en `orquestador.py`, `main.py`, `config_rutas_ext_y_archivos.yaml`, `cargador_parametros._CATALOGO` y ambos scripts de carga GCP (dly + hist).
3. **Migrar** `.XLSM` + macros VBA a `.xlsx` + Python (email/control via `core.email_report` y `core.control_interfaces`).
4. **Externalizar** `FACTOR_CORE_R13 = 0.70` a parámetros y migrar `parametros_ssv.xlsx` a JSON (`tools.excel_a_json`).
5. **Limpiar** el SQL (bug de `OR`/`AND` en el `HAVING`) y vectorizar el loop por producto.
6. **Documentar** en `docs/modelos/ssv.md` y sumar al flujo de `primera_vuelta/segunda_vuelta`.

Estimación gruesa: ~2 días de trabajo (1 día reescritura + wiring orquestador/GCP; 1 día migración XLSM→email Python, tests y documentación).
