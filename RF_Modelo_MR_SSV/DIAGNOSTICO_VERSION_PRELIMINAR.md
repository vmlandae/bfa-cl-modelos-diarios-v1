# Modelo SSV — Diagnóstico de la versión preliminar

Rama: `feat/modelo-ssv`
Fecha: 2026-04-20
Alcance: primera iteración productiva del modelo SSV a partir del zip entregado por metodología (`MR_SSV.zip`, commits `de79d6d` + `d7fcf7a` de esta rama).

---

## 1. Resumen ejecutivo

**Lo que entregamos en esta versión preliminar:**

- Carpeta `RF_Modelo_MR_SSV/` con `mr_ssv.py` reescrito siguiendo el patrón del repo (igual al de `ml_nmd`/`ml_lc`): YAML de rutas, cache parquet compartido, `core.excel_output`, `core.logger`, firma `ejecutar_modelo(fecha) -> bool`.
- Parámetros migrados a `RF_Modelo_MR_SSV/parametros/` con una hoja nueva `FACTORES` que externaliza el antiguo `FACTOR_CORE_R13 = 0.70` hardcodeado. JSON sibling generado con `tools.excel_a_json` (extendido para soportar columnas datetime).
- Integración end-to-end en los 7 puntos de cableado del pipeline:
  1. `config/config_rutas_ext_y_archivos.yaml`
  2. `procesamiento_datos_input/cargador_parametros._CATALOGO`
  3. `core/orquestador.py` (vuelta 2, orden 10)
  4. `main.py` MODELO_A_TABLAS
  5. `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py` (tarea `mr_ssv`)
  6. `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` (config `report_mr_ssv_hist`)
  7. `core/email_report.py` `TABLAS_SEGUNDA_VUELTA`
- Documentación del modelo en `docs/modelos/ssv.md` + entrada en `mkdocs.yml`.
- Bugs detectados del código heredado corregidos (detalle abajo).
- Smoke test offline con balance sintético confirma: shape esperado 832 filas, sumas CORE/NON_CORE consistentes, fechas R13 arrancan en fin del mes siguiente, PMP de `CTA_CTE` (4.42) coincide con el valor del XLSM heredado.

**Lo que NO entregamos en esta iteración** (pendiente — ver §5):

- Corrida productiva real (requiere Access/UNC y GCP credenciales, no disponibles en este entorno de desarrollo).
- Migración de las macros VBA (`control_y_correo_diario`, etc.) a equivalentes en Python.
- Confirmación con metodología de las dudas listadas en §4.

---

## 2. Cambios aplicados respecto al código heredado

### 2.1 Estructura e integración

| Archivo | Cambio | Por qué |
|---|---|---|
| `RF_Modelo_MR_SSV/__init__.py` | Nuevo, vacío. | Habilita `from RF_Modelo_MR_SSV.mr_ssv import ejecutar_modelo`, el modo que usa el orquestador. |
| `RF_Modelo_MR_SSV/mr_ssv.py` | Reescrito desde cero (470 LOC vs 516 del heredado). | Mismo shape de output pero con imports del repo, logger, validador, firma estándar y eliminación de todas las macros COM. |
| `RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.xlsx` | Copia + nueva hoja `FACTORES`. | Externaliza `FACTOR_CORE_R13=0.70` del código. |
| `RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.json` | Generado con `tools.excel_a_json`. | Lectura 10-50× más rápida que Excel y diffable en git. |
| `config/config_rutas_ext_y_archivos.yaml` | Bloque `mr_ssv:` con 5 claves (`ms_access_input`, `ms_access_tabla_input`, `excel_parametros_modelo_input`, `excel_parametros_core_input`, `excel_output`). | Patrón idéntico al de `ml_nmd`/`ml_lc`. |
| `procesamiento_datos_input/cargador_parametros.py` | Entrada `mr_ssv` en `_CATALOGO`. | Activa validación JSON↔Excel con caché y auto-fallback. |
| `tools/excel_a_json.py` | Pre-conversión de columnas datetime64 a ISO strings (`%Y-%m-%d`); entrada `mr_ssv` en catálogo. | Las hojas de SSV tienen columnas de fecha; el encoder anterior rompía en `Timestamp`. Ahora matchea `astype(str)` de datetime64 → compatible con el validador existente. |
| `core/orquestador.py` | Modelo registrado en vuelta 2. | Comparte fuente Access (`RF_BD_Gestion_RL`) con `ml_nmd` y `ml_lc` — aprovecha parquet del día. |
| `main.py` | `'mr_ssv': ['report_mr_ssv_dly']` en `MODELO_A_TABLAS`. | Muestra el estado de carga GCP en el resumen. |
| `carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py` | Tarea `mr_ssv` con `DESARROLLO` → `report_mr_ssv_dly`, esquema base, TRUNCATE. | Estándar del resto de modelos. |
| `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` | Config hist `report_mr_ssv_dly` → `report_mr_ssv_hist`, partición `FECHA_PROCESO` + entrada `MODELO_A_TABLAS`. | Consolidación histórica con el mismo pattern. |
| `core/email_report.py` | `report_mr_ssv_hist` en `TABLAS_SEGUNDA_VUELTA`. | El modelo queda incluido automáticamente en el mail diario de segunda vuelta. |
| `docs/modelos/ssv.md`, `mkdocs.yml` | Doc metodológica nueva + nav entry. | Completitud con los otros modelos. |

### 2.2 Fixes/optimizaciones aplicados al heredado

1. **SQL — filtro correcto**: el heredado tenía un `HAVING` con `OR` sin paréntesis que hacía interpretar mal el predicado y arrastraba `DAP` y `LINEA DE CREDITO` (que luego no se usaban). Reemplazado por filtro `pandas` sobre los 4 sub-productos exactos después de leer la tabla desde cache — los mismos 4 que aparecen en `CUOTAS_SSV`.
2. **Lectura Access**: de `ut.lectura_datos_ms_access` (consulta síncrona cada día) a `leer_tabla_con_cache` — si `ml_nmd` o `ml_lc` corrieron antes el mismo día (misma vuelta 2), el parquet ya existe y la lectura es ~instantánea.
3. **Concat incremental → concat final**: el loop heredado hacía `pd.concat([tabla_desarrollo, nueva_fila])` dentro del loop → O(n²). Ahora acumula en una lista y hace un único `pd.concat` al final.
4. **Función `_generar_fechas_cuotas_r13`**: aisla la lógica "fin-de-mes desde el mes siguiente" (la primera cuota nunca cae en el mes de proceso, para separar del `NON_CORE` que sí vence a +1 día). Se verificó equivalencia con la lógica heredada: para `fecha_proceso=2025-10-06` produce `[2025-11-30, 2025-12-31, 2026-01-31, ...]` — idénticas al heredado.
5. **Helper `_bloque_filas`**: DRY para los 6 tipos de bloques de filas. Preserva el orden exacto de columnas que espera el cargador BQ (`_COLS_DESARROLLO` hard-set al final de `construir_tabla_desarrollo`) e incluye la columna `TASA` (el heredado no la tenía pero el esquema BQ sí la espera; `cargar_dataframe_bigquery` toleraba la ausencia porque era `NULLABLE`, pero es más prolijo tenerla).
6. **Validación temprana** (`validar_datos_iniciales`): se aborta antes de construir la tabla si falta balance de algún producto, o `CUOTAS_SSV/DISTR_CORE_SSV_R13` no cubre los 4 productos, o `DISTR_CORE_R13` no suma 1.0 por producto (tolerancia 1e-6).
7. **Externalización de `FACTOR_CORE_R13`**: nueva hoja `FACTORES` en el parámetro Excel. El código hace fallback a 0.70 si la hoja no existe, lo que mantiene compatibilidad con versiones antiguas del parámetro en red durante la transición.
8. **Moneda tomada de `CUOTAS_SSV`** (canonical por producto), no del balance. El heredado lo hace así pero no estaba explícito; ahora está comentado.
9. **Eliminación de macros VBA**: se removió todo el bloque `pythoncom`/`ejecutar_macro_excel` y las llamadas a `control_y_correo_diario`, `actualiza_dinamica_control`, etc. El control diario ahora lo hace `core.email_report` al ejecutarse `--modelos segunda_vuelta` (lee `report_mr_ssv_hist` y compara t vs t-1 vía BigQuery).
10. **Logger estructurado**: de `print(...)` a `core.logger.get_logger(__name__)` + `print` de encabezado preservado (se mantiene para compatibilidad con cómo el orquestador actual logguea progreso en la consola).

### 2.3 Bits del heredado que se preservaron deliberadamente

Algunas convenciones del código original parecen *raras* pero decidí **no tocarlas** porque tienen impacto en el sistema downstream:

1. **Filas "agregado" con `CODIGO_PRODUCTO == CODIGO_SUBPRODUCTO`** (bloques `core_r13_agr` y `non_core_r13_agr` de la vista R13). En el XLSM heredado estas filas aparecen así a propósito — son totales convenientes para el pivot del reporte normativo. Las mantuve idénticas.
2. **`MT.CTA. VISTA` con punto** en `P_CODIGOS_PRODUCTOS["CTA_VTA"]["COD_PRO_GESTION"]` (mientras el resto usa guión bajo `MT_CTA. …`). Es una inconsistencia histórica pero el sistema consumidor la espera así.
3. **Hoja `DATOS` = resumen + inputs con prefijo `INPT_`** (mismo formato que el heredado). Es un artefacto útil para auditar qué input se usó en cada corrida.
4. **Primera cuota R13 siempre en el mes siguiente** al de fecha de proceso (aunque `fecha_proceso` no sea fin de mes). Es la semántica del heredado y genera la "brecha" entre el `NON_CORE` (vencimiento +1 día) y el `CORE` distribuido.

### 2.4 Shape observado (ejecución offline sobre parámetros reales)

```
DESARROLLO: 832 filas × 31 columnas
  CTA_CTE:  42 cuotas GES  +  1 NON_GES  +  74 CORE_R13 + 3 agr/non  =  120
  CTA_VTA:  42 cuotas GES  +  1 NON_GES  + 108 CORE_R13 + 3 agr/non  =  154
  AGD:     205 cuotas GES  +  1 NON_GES  +  70 CORE_R13 + 3 agr/non  =  279
  AGI:     205 cuotas GES  +  1 NON_GES  +  70 CORE_R13 + 3 agr/non  =  279
```

La versión XLSM heredada tenía 833 filas incluyendo la fila de header (832 + 1). **Match.**

---

## 3. Verificaciones realizadas

| Chequeo | Resultado |
|---|---|
| `python -m py_compile RF_Modelo_MR_SSV/mr_ssv.py` | OK (sintaxis válida). |
| `python -m tools.excel_a_json mr_ssv` | OK (41 KB JSON, 3 hojas). |
| Reload JSON → DataFrame → check columnas y dtypes | OK. `FECHA_VENCIMIENTO_CUOTA` recuperada como datetime tras `pd.to_datetime`. |
| Suma `DISTR_CORE_R13` por producto ≈ 1 | OK (1.0 ± 1e-15 en los 4 productos). |
| `validar_datos_iniciales(...)` con insumos válidos | OK. |
| `construir_tabla_desarrollo(...)` shape | 832 filas × 31 columnas. |
| `construir_tabla_desarrollo(...)` sumas | Para los 4 productos: `Σ(CORE_distr) = monto_core_r13`, `CORE_agr = monto_core_r13`, `NON_CORE = FLUJO − monto_core_r13`. |
| `_generar_fechas_cuotas_r13(2025-10-06, N)` | `[2025-11-30, 2025-12-31, 2026-01-31, 2026-02-28, 2026-03-31, ...]`. Primera cuota = fin del mes siguiente. |
| `calcular_resumen_control` | 24 filas (8 product×subproduct por producto × 4 − duplicados) con PMP y min/max fechas. PMP de `CTA. CORRIENTE PERSONAS_CORE` = 4.421524 (coincide con el valor heredado 4.421523500). |
| Wiring YAML/orquestador/main/dly/hist/email_report | Todos los puntos verificados programáticamente. |
| `segunda_vuelta` expandida incluye `mr_ssv` | OK (`[mr_prepago_cmr, ml_nmd, ml_lc, ml_inversiones, mr_ssv]`). |

**Pendiente de ejecución real** (requiere entorno Windows con ODBC/Access + credenciales GCP):

- Corrida completa `python main.py --fecha <hoy> --modelos mr_ssv`.
- Comparar el `DESARROLLO` generado contra el `DESARROLLO` del XLSM heredado de la misma fecha (debería ser idéntico fila a fila, salvo por la columna `TASA` que agregamos como NaN y por el orden si el heredado no estaba estable).
- Carga a `report_mr_ssv_dly_test` y validar en BQ.

---

## 4. Dudas para metodología / negocio

Preguntas que surgieron al estudiar el código heredado y que necesitan confirmación antes de considerar el modelo "cerrado":

### 4.1 Dudas de modelamiento

1. **`FACTOR_CORE_R13 = 0.70`**. ¿Es un parámetro estable o varía? Si varía (escenarios de stress, cambios normativos), ¿con qué cadencia? Hoy está externalizado a `FACTORES` pero con un solo valor; si el ciclo lo requiere (p. ej. distinto por moneda o por producto), habría que rediseñar la tabla.

2. **Cuotas de `CUOTAS_SSV` con fechas hardcodeadas**. Las fechas de vencimiento están precalculadas en el Excel (p. ej. `CTA_CTE` va de 2025-10-31 a 2029-03-31). ¿Cuál es el responsable y la periodicidad de refresco? ¿Qué pasa si la corrida es de una fecha > última fecha disponible (p. ej. corremos 2029-04 y la última cuota expira en 2029-03-31)? Probablemente el modelo produciría un desarrollo "sin futuro" para ese producto.

3. **`DISTR_CORE_SSV_R13`** tiene entre 70 y 108 cuotas por producto (distinto por producto). ¿Ese número refleja un *horizonte* metodológico o se fue acumulando con el tiempo? Si el objetivo es un horizonte fijo (p. ej. 10 años = 120 meses), convendría uniformar.

4. **Filas "agregadas" con `CODIGO_PRODUCTO == CODIGO_SUBPRODUCTO`** en la vista R13 (secciones 2.3.1 y 3 de la doc). ¿Son un requerimiento del consumidor downstream o un artefacto histórico? Si es lo segundo, se podrían eliminar y simplificar el output.

5. **CTA_VTA usa `MT.CTA. VISTA` (con punto)** y el resto usa `MT_CTA. X` (con guión bajo). ¿Es intencional? El sistema downstream debe aceptar ambos, pero es una inconsistencia que idealmente corregiríamos en coordinación con el consumidor.

6. **Moneda `CLF` vs `UF`**. El core vigente en `saldos_core.xlsx` llega como `AGD_UF` y `AGI_UF` pero el modelo siempre los trata como `CLF`. ¿Confirmamos que `AGD_UF == AGD (CLF)` o hay un caso donde difieren?

7. **`FLUJO_MO = AMORTIZACION_MO + INTERES_MO`** se usa como "saldo" para la partición CORE/NON_CORE. ¿Es esa la definición correcta para SSV (flujo) o debería ser el saldo vigente del producto? En `ml_nmd` se usa `FLUJO_MO` también y ahí tiene sentido para productos con pagos; pero para una cuenta vista no hay amortización contractual, así que probablemente `FLUJO_MO ≈ saldo`. Confirmar.

### 4.2 Dudas de integración

8. **Macros de Excel (XLSM)**: las 4 macros del heredado (`control_y_correo_diario`, `actualiza_dinamica_control`, `enviar_correo_Outlook`, `control_comparacion_dia`) hoy ya no se ejecutan en la versión preliminar. El control diario debería hacerlo `core.email_report` vía BigQuery, que ya está activado (`report_mr_ssv_hist` en `TABLAS_SEGUNDA_VUELTA`). ¿Hay algún consumidor interno que aún dependa directamente del XLSM abierto con el pivot `CONTROL`?

9. **Cadencia de publicación**: ¿el output `mr_ssv.xlsx` se lee directamente desde la ruta local o hay un *sync* a una ruta de red que el heredado hacía implícitamente al dejar el archivo en `\\vmdvorak\...\MR_SSV\mt_ssv_local_cc.XLSM`? Si es lo segundo, hay que añadir ese paso al `guardar_excel` o documentarlo.

10. **Nombre de tabla BQ**: propongo `report_mr_ssv_dly` / `report_mr_ssv_hist` siguiendo el patrón. Si metodología/negocio prefiere otro nombre (p. ej. `report_mr_nmd_r13_dly` para reflejar mejor la vista), conviene decidirlo antes de crear la tabla en BQ.

### 4.3 Dudas técnicas menores

11. **Columna `TASA` agregada** (era 30 columnas en el heredado, ahora 31). El esquema BQ la espera como `NULLABLE`. Sin uso hoy, pero dejarla como NaN evita futuras sorpresas.

12. **Hoja `DATOS`** mezcla resumen + inputs prefijados `INPT_`. ¿La consume alguien o era solo auditoría visual en el XLSM? Si no la usa nadie, se puede simplificar a `RESUMEN_HIST` único.

13. **`saldos_core.xlsx`** está en red y sólo se usa el `CORE_VIGENTE`. Si en algún momento el archivo cambia de formato (p. ej. se agrega/quita una columna), se rompería silenciosamente en el `rename + T`. Sería prudente validar la forma esperada dentro del cargador.

---

## 5. Roadmap

Prioridad: **A** = debe hacerse antes de marcar el modelo como productivo; **B** = mejora importante post-salida; **C** = backlog.

### Fase 1 — Cerrar la versión preliminar (A)

- [ ] **Corrida real end-to-end**: ejecutar `python main.py --fecha <fecha_con_data> --modelos mr_ssv --cargar-gcp` en el entorno Windows con acceso a Access/red/GCP.
- [ ] **Diff DESARROLLO**: comparar `RF_Modelo_MR_SSV/mr_ssv.xlsx` vs `MR_SSV/mt_ssv_local_cc.XLSM` hoja `DESARROLLO` para la misma fecha. Esperado: mismas filas, mismas sumas (±epsilon en `DISTR_CORE_R13 * core`). Diferencia esperada: columna `TASA` que agregamos.
- [ ] **Tabla BQ de test**: crear `report_mr_ssv_dly_test` y `report_mr_ssv_hist_test`, cargar con esa tabla varias fechas (2025-10-01, 2025-10-31, 2026-01-31) y validar partición/totales.
- [ ] **Reunión con metodología**: repasar dudas §4.1.1–§4.1.7.
- [ ] **Decisiones de producto** §4.2.8–§4.2.10 con el dueño del reporte downstream.
- [ ] **Habilitar en automático**: agregar `mr_ssv` al `run_diario.bat` (vuelta 2) una vez validado.

### Fase 2 — Hardening (B)

- [ ] **Unit tests**: pytest para `_generar_fechas_cuotas_r13`, `construir_tabla_desarrollo` con fixtures mínimas (1 producto × 3 cuotas) y assertions de shape + sumas. Un test debería replicar la corrida offline de §3 para evitar regresiones.
- [ ] **Refresco automatizado de `CUOTAS_SSV`**: si metodología confirma cadencia (p. ej. mensual), crear un script que valide que las cuotas cubran al menos N años hacia adelante y alerte cuando queden menos de X cuotas por vencer.
- [ ] **Vectorizar `construir_tabla_desarrollo`**: hoy el loop por 4 productos es trivial (~10ms) pero si crecen a 10+ productos conviene reescribir usando `DataFrame.from_records` por tipo de bloque. Baja prioridad.
- [ ] **Migrar `saldos_core.xlsx` a JSON + validador**: mismo tratamiento que `parametros_mr_ssv.xlsx`. Beneficio: el archivo en red puede cambiar sin avisar; un JSON local con snapshot day-0 da reproducibilidad.
- [ ] **Control de interfaces día a día**: si el consumidor final (interfaz PML) pasa a consumir desde BQ en lugar del XLSM, registrar también `mr_ssv` en `core.control_interfaces` si aplica.

### Fase 3 — Mejoras metodológicas (C — coordinación con Riesgo Financiero)

- [ ] **Unificación con `ml_nmd`**: ambos modelos consumen los mismos 4 productos. Evaluar si se puede crear una base común de insumos (mismo dataframe agregado) para evitar re-lecturas y mantener coherencia en los filtros.
- [ ] **Parametrizar `FACTOR_CORE_R13` por producto/moneda**: si el factor varía por clase de producto según el reporte R13, extender la hoja `FACTORES` a una estructura `{PRODUCTO, MONEDA, FACTOR}`.
- [ ] **Revisar convención "agregado"** (filas con product==subproduct): si el consumidor downstream permite eliminarlas, quitar esas 8 filas por producto simplifica el output y la lectura.
- [ ] **Eliminar el XLSM heredado** (`MR_SSV/mt_ssv_local_cc.XLSM`) de la ruta de red una vez que todos los consumidores estén migrados a la versión Python.
- [ ] **Documentación metodológica completa**: anexar al `docs/modelos/ssv.md` la *base metodológica* del modelo (decisiones de diseño R13, fuentes de las cuotas, referencias a la Circular 3.565).

### Fase 4 — Limpieza (C)

- [ ] Borrar `MR_SSV.zip` del repo (se dejó ahora como referencia; el contenido está trackeado en el commit `de79d6d`).
- [ ] Borrar `MR_SSV/` (código heredado) una vez que la versión `RF_Modelo_MR_SSV/` lleve ≥1 mes en producción sin issues.
- [ ] Borrar `MR_SSV/OTROS/*.XLSM` (son backups intermedios sin valor histórico).

---

## 6. Archivos tocados en esta iteración (resumen para revisión)

```
A  RF_Modelo_MR_SSV/__init__.py
A  RF_Modelo_MR_SSV/mr_ssv.py
A  RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.xlsx
A  RF_Modelo_MR_SSV/parametros/parametros_mr_ssv.json
A  RF_Modelo_MR_SSV/DIAGNOSTICO_VERSION_PRELIMINAR.md  (este archivo)
A  docs/modelos/ssv.md
M  mkdocs.yml                                              (+1 línea nav)
M  config/config_rutas_ext_y_archivos.yaml                 (+7 líneas bloque mr_ssv)
M  procesamiento_datos_input/cargador_parametros.py        (+1 línea _CATALOGO)
M  tools/excel_a_json.py                                   (+1 entrada + fix datetime)
M  core/orquestador.py                                     (+9 líneas registro)
M  main.py                                                 (+1 línea MODELO_A_TABLAS)
M  carga_modelos_gcp/cargar_output_modelos_bigquery_dly.py (+9 líneas tarea)
M  carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py (+8 líneas config + 1 MODELO_A_TABLAS)
M  core/email_report.py                                    (+1 línea TABLAS_SEGUNDA_VUELTA)
```
