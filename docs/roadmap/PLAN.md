# Plan de Ejecución — Roadmap BFA-CL Modelos Diarios

> **Fuente de verdad del roadmap:** [`roadmap.yaml`](roadmap.yaml)
> **Ultima actualizacion:** 2026-04-24
> **Equipo:** Victor Landaeta (`@vlandaetat`), Rodrigo Munoz (`@rmunozb`)

---

## ⚠️ DESTACADO — F27: Automatizar saldos CORE mensuales (MR SSV)

> **Estado:** backlog · **Prioridad:** alta · **Responsable:** @vlandaetat

Los saldos CORE mensuales que alimentan MR SSV se incorporan HOY **manualmente**
mediante `RF_Modelo_MR_SSV/parametros/agregar_core_hardcode.py`, que hardcodea
valores en `parametros_mr_ssv.xlsx/json`. La proxima actualizacion CORE (semana
siguiente al merge de `feat/modelo-ssv`) debe usarse para:

1. **Documentar paso a paso** el procedimiento manual actual en
   `docs/modelos/ssv.md` (fuente oficial, como se extraen los saldos, como se
   pegan en parametros, validacion visual).
2. **Disenar la utilidad automatizada** que reemplace el hardcode leyendo la
   fuente oficial CORE y actualizando `parametros_mr_ssv` sin intervencion.
3. **Agregar validacion defensiva** en `mr_ssv.py`: si los CORE no estan
   actualizados al corte EOM, abortar con mensaje claro.

Riesgo actual: error humano alto si se olvida ejecutar el script o si cambia
el layout de las planillas CORE.

---

## Convenciones

| Símbolo | Significado |
|---------|-------------|
| `[ ]` | Pendiente |
| `[~]` | En progreso |
| `[x]` | Completado |
| `@vlandaetat` / `@rmunozb` | Responsable asignado |
| `❓` | Pregunta abierta / por validar |
| `⚠️` | Riesgo o bloqueante |

---

## Resumen de Sprints

| Sprint | Fechas | Objetivo | Features |
|--------|--------|----------|----------|
| **S1** | Feb 25 -> Mar 7 | Quick Wins & Fundamentos | F02, F16, F14, F13, F15, F11 |
| **S2** | Mar 10 -> Mar 21 | Observabilidad Core | F01, F12, F26, DQW |
| **S3** | Mar 24 → Abr 4 | Validación & Alertas | F03, F17, F09 |
| **S4** | Abr 7 → Abr 18 | Datos Históricos & Legacy | F18, F19 |
| **S5** | Abr 21 → May 9 | UX & Playground | F04, F06 |

---

## S1 — Quick Wins & Fundamentos (Feb 25 → Mar 7)

### F02: Máquina del Tiempo — Snapshots de parámetros ✅

> **Tamaño:** XS (~0.5d) · **Asignado:** @vlandaetat · **Completado:** 2026-02-27

**Qué:** `shutil.copy` de Excel de parámetros antes de cada ejecución → `snapshots/{fecha}/{modelo}/`

**Archivos:**
- `core/orquestador.py` — agregar método `_snapshot_parametros()`
- Paths ya en `config/config_rutas_ext_y_archivos.yaml` bajo `excel_parametros_input`

**Tareas:**
- [x] Implementar `_snapshot_parametros(modelo_key, fecha)` en `OrquestadorModelos`
- [x] Leer rutas de `excel_parametros_input` del YAML por modelo
- [x] Copiar con `shutil.copy2` a `snapshots/{YYYYMMDD}/{modelo_key}/`
- [x] Manejar error de red → abortar modelo (raise RuntimeError)
- [x] Llamar en `ejecutar_modelo()` justo antes de `modelo.ejecutar_modelo(fecha)`
- [ ] Verificar que funciona para `ml_inversiones` (parámetros en red UNC)
- [ ] Verificar overhead < 2s

**Preguntas resueltas:**
- [x] ✅ ¿Incluir CSVs de interfaz? → No, solo Excel de parámetros
- [ ] ❓ ¿Política de retención? ¿Borrar snapshots > N días automáticamente?
- [x] ✅ Si la red no está disponible → abortar modelo (RuntimeError)

**Prompt sugerido:**
```
Implementa un método `_snapshot_parametros(modelo_key, fecha)` en `OrquestadorModelos`
(core/orquestador.py) que:
1. Lea `excel_parametros_input` del YAML de config para el modelo
2. Copie con `shutil.copy2` a `snapshots/{fecha_YYYYMMDD}/{modelo_key}/`
3. Maneje errores de red sin bloquear la ejecución (try/except + log)
4. Se llame en `ejecutar_modelo()` justo antes de `modelo.ejecutar_modelo(fecha)`
Log con print() por ahora (F11 migrará después).
```

---

### F16: Ejecución Idempotente — DELETE + INSERT en históricos ✅

> **Tamaño:** S (~1d) · **Asignado:** @vlandaetat · **Completado:** 2026-02-28

**Qué:** Permitir re-inserción segura en tablas históricas BQ con flag `--force-historico`,
backup CSV automático y metadata de auditoría.

**Archivos:**
- `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` — `_exportar_backup_pre_delete()`, `consolidar_historico_por_tabla()`, `consolidar_historico_bigquery()`
- `core/orquestador.py` — `consolidar_historico_gcp(force=)`, `parse_arguments()`
- `main.py` — `--force-historico` flag
- `.gitignore` — `backups_historicos/`

**Contexto:** Comportamiento por defecto: si datos existen → omite inserción (seguro).
Con `--force-historico`: exporta backup CSV → DELETE → INSERT, con metadata JSON y logging completo.

**Decisiones tomadas:**
- **Por defecto** se omite inserción si datos existen (no DELETE automático).
- **`--force-historico`** activa: backup CSV con timestamp + metadata JSON + DELETE + INSERT.
- El backup se guarda en `backups_historicos/{YYYYMMDD}/{tabla}/` con timestamp.
- Se generan 2 archivos de metadata: uno pre-DELETE (datos exportados) y uno post-INSERT (datos insertados).
- Si el backup falla, se aborta sin ejecutar DELETE.
- Todo queda en el logger (JSONL) para auditoría.

**Tareas:**
- [x] Implementar `_exportar_backup_pre_delete()` — lee registros de BQ, guarda CSV + metadata JSON
- [x] Modificar `consolidar_historico_por_tabla(force=False)` con comportamiento dual:
  - Sin force: omite si datos existen
  - Con force: backup → DELETE → INSERT → metadata post-INSERT
- [x] Propagar `force` en `consolidar_historico_bigquery()` y `consolidar_historico_gcp()`
- [x] Agregar `--force-historico` en `main.py` y `orquestador.py`
- [x] Migrar prints a logger en todo `cargar_output_modelos_bigquery_hist.py`
- [x] Agregar `backups_historicos/` a `.gitignore`
- [x] Documentar comportamiento en docstrings
- [ ] Test: ejecutar consolidación 2 veces con --force-historico → `COUNT(*)` idéntico
- [ ] Test: verificar que CSV de backup contiene mismas filas que se eliminan

**Preguntas resueltas:**
- [x] ✅ ¿Columna de fecha? → Siempre `FECHA_PROCESO` (definida en `COLUMNA_FECHA_PARTICION` por tabla)
- [x] ✅ ¿Flag o por defecto? → Flag `--force-historico`. Por defecto omite (seguro).
- [x] ✅ ¿Backup antes de DELETE? → Sí, CSV con timestamp + metadata JSON. Aborta si falla.
- [ ] ❓ ¿Tablas históricas particionadas por fecha en BQ?

**Prompt sugerido:**
```
En `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py`, modifica
`consolidar_tabla()` para que:
1. Si datos existen para la fecha, ejecute DELETE FROM {tabla} WHERE
   fecha_proceso = '{fecha}' antes de insertar
2. Loguee el DELETE realizado con cantidad de filas eliminadas
3. Mantenga el INSERT existente sin cambios
4. Agrega un test que verifique que dos ejecuciones producen el mismo COUNT(*)
```

---

### F14: Cache de Primera Vuelta — CSV de red a parquet local ✅

> **Tamaño:** S (~2d) · **Asignado:** @vlandaetat · **Completado:** 2026-02-27

**Qué:** Cachear `ProductosMercadoLiquidezGCP*.txt` de red como parquet local,
con copia raw + metadatos (timestamp, checksum MD5) para trazabilidad.

**Archivos modificados:**
- `procesamiento_datos_input/cache_tablas.py` — funciones nuevas: `copiar_interfaz_a_local()`,
  `leer_interfaz_con_cache()`, `verificar_interfaz_post_ejecucion()`,
  helpers `_md5_archivo()`, `_guardar_metadata()`, `_leer_metadata()`, `_resolver_rutas_interfaz()`
- `core/orquestador.py` — hooks pre/post ejecución primera vuelta
- `RF_Modelo_Prepago_Consumo/mr_prepago_consumo.py`
- `RF_Modelo_Prepago_Hipotecario/mr_prepago_hipotecario.py`
- `RF_Modelo_Mora_Consumo/ml_mora_consumo.py`
- `RF_Modelo_Mora_CAE/ml_mora_cae.py`
- `RF_Modelo_Mora_Hipotecario/ml_mora_hipotecario.py`
- `RF_Modelo_Mora_Comercial/ml_mora_comercial.py`

**Contexto:** `cache_tablas.py` ya implementaba cache parquet para Access (segunda vuelta).
F14 extiende este módulo para cubrir también la interfaz CSV de primera vuelta.

**Decisiones tomadas:**
- El CSV a veces cambia durante el día (correcciones). Se verifica checksum MD5
  **post-ejecución** (una sola vez) y se emite **warning** si el archivo de red
  cambió vs la copia local durante la ejecución.
- Se cachea el CSV **completo** (sin filtrar por modelo). Cada modelo aplica su propio
  filtro de SISTEMA/CODIGO_PRODUCTO/subproductos después. La ganancia de performance
  de cachear filtrado no justifica la complejidad.
- El nombre del archivo incluye la fecha de proceso (`ProductosMercadoLiquidezGCP{YYYYMMDD}.txt`),
  que generalmente es el día hábil anterior.
- Se guarda `.txt` raw **100% sin modificar** en `data/cache/raw/` para auditoría.
- Caché filtrado por modelo: descartado (TODO futuro solo si mediciones muestran necesidad).

**Arquitectura pre/post (arreglo de race condition):**
- **PRE-ejecución** (orquestador, hilo principal, 1 vez): `copiar_interfaz_a_local()` copia
  .txt de red → `data/cache/raw/`, protegido con `threading.Lock`.
- **Durante ejecución** (N hilos): `leer_interfaz_con_cache()` lee SOLO desde local/parquet,
  nunca toca la red. Fallback a red solo si se ejecuta sin orquestador.
- **POST-ejecución** (orquestador, hilo principal, 1 vez): `verificar_interfaz_post_ejecucion()`
  compara checksum local vs red y emite WARNING si cambió.

**Tareas:**
- [x] Implementar `copiar_interfaz_a_local()` — copia raw .txt + metadata JSON (timestamp, MD5)
- [x] Implementar `leer_interfaz_con_cache()` — parquet cache + lectura desde copia local
- [x] Respetar `CACHE_FORZAR_RECARGA` existente
- [x] Warning si checksum de red difiere de copia local en re-ejecución
- [x] Modificar `mr_prepago_consumo.py` → usa `leer_interfaz_con_cache()`
- [x] Modificar `mr_prepago_hipotecario.py`
- [x] Modificar `ml_mora_consumo.py`
- [x] Modificar `ml_mora_cae.py`
- [x] Modificar `ml_mora_hipotecario.py`
- [x] Modificar `ml_mora_comercial.py`
- [x] Eliminar boilerplate duplicado de lectura CSV en cada modelo (columnas, dtypes, strip, datetime)
- [x] Fix race condition: copia pre-ejecución (1 vez), verificación post-ejecución (1 vez)
- [x] `threading.Lock` para seguridad en ejecución individual sin orquestador
- [x] Hooks `_pre_ejecucion_primera_vuelta()` y `_post_ejecucion_primera_vuelta()` en orquestador
- [ ] Test: primera ejecución crea `.parquet` en `data/cache/` y `.txt` en `data/cache/raw/`
- [ ] Test: segunda ejecución sin red funciona desde cache
- [ ] Test: `--forzar-recarga` re-lee de red

**Preguntas resueltas:**
- [x] ✅ ¿El CSV cambia durante el día? → A veces sí (correcciones). Se compara checksum.
- [x] ✅ ¿Cachear completo o filtrado? → Completo. Filtro por modelo se aplica después.
- [x] ✅ ¿Nombre incluye fecha? → Sí: `ProductosMercadoLiquidezGCP{YYYYMMDD}.txt`

---

### F13: Pre-flight Checks — Verificación de dependencias ✅

> **Tamaño:** S (~2d) · **Asignado:** @vlandaetat · **Completado:** 2026-03-12

**Qué:** Health checks de rutas de red, bases Access, Excel de parámetros
y driver ODBC ANTES de ejecutar modelos

**Archivos:**
- `core/preflight.py` (nuevo)
- `core/orquestador.py` — integrado en `ejecutar_modelos_paralelo()` y `ejecutar_modelo_secuencial()`

**Contexto:** Si la red está caída, el error aparece minutos después cuando `pyodbc.connect()` falla con timeout.

**Tareas:**
- [x] Crear `core/preflight.py` con dataclasses `CheckResult` / `PreflightReport`
- [x] Parsear YAML para obtener rutas de red y Access por modelo seleccionado
- [x] Verificar accesibilidad de rutas de red, Excel de parámetros, bases Access
- [x] Verificar driver ODBC Access instalado
- [x] Deduplicar rutas compartidas entre modelos
- [x] Integrar en `orquestador.py` (ambos métodos de ejecución)

**Notas:** Rama `feat/F13-preflight-checks` (3e7889b), mergeado a `main`.

**Preguntas por resolver:**
- [ ] ❓ ¿`os.path.exists()` es suficiente o hay que intentar abrir los archivos?
- [ ] ❓ ¿Pre-flight siempre activo, o solo con flag `--preflight`?
- [ ] ❓ ¿Proponer subconjunto de modelos que sí pueden correr, o abortar?

**Prompt sugerido:**
```
Crea `core/preflight.py` con clase `PreflightChecker` que:
1. Reciba lista de modelos seleccionados
2. Lea config YAML para obtener rutas de red y Access por modelo
3. Verifique accesibilidad con os.path.exists() + os.access()
4. Para Access: pyodbc.connect() con timeout 5s
5. Retorne dict {modelo: {ok: bool, errores: [str]}}
En orquestador.py, llamar pre-flight antes de ejecutar_modelos_paralelo()
y permitir continuar solo con modelos que pasaron.
```

---

### F15: Testing Mínimo Viable — Tests de configuración

> **Tamaño:** S (~2d) · **Asignado:** `________`

**Qué:** Tests que validan configuración sin dependencias externas

**Archivos:**
- `tests/` (directorio nuevo)
- `tests/conftest.py`, `tests/test_config.py`, `tests/test_imports.py`

**Contexto:** `pytest` ya está en requirements.txt. `RF_Modelo_Inversiones/tests/` tiene 8 tests como referencia.

**Tareas:**
- [ ] Crear `tests/conftest.py` con fixtures comunes (paths, config loader)
- [ ] Crear `tests/test_imports.py` — test parametrizado que importa cada módulo del orquestador y verifica `callable(mod.ejecutar_modelo)`
- [ ] Crear `tests/test_config.py` — parsea YAML y verifica: es válido, cada modelo del orquestador tiene entrada, rutas relativas existen
- [ ] Verificar que `pytest tests/ -v` pasa sin acceso a red
- [ ] Verificar que `pytest tests/ --co` lista 15+ tests
- [ ] Agregar a `.gitignore` si hay artifacts de test

**Preguntas por resolver:**
- [ ] ❓ ¿Hay CI/CD (GitLab CI) donde se ejecutarían automáticamente?
- [ ] ❓ ¿Tests deben correr sin `bfa_cl_utilidades` (mock de imports)?
- [ ] ❓ ¿Test smoke de `callable(ejecutar_modelo)` para los 10 modelos?

**Prompt sugerido:**
```
Crea tests/ en la raíz del proyecto:
- tests/conftest.py con fixtures (BASE_DIR, config YAML parseada)
- tests/test_imports.py: test parametrizado que importa cada módulo del
  orquestador y verifica que ejecutar_modelo existe y es callable
- tests/test_config.py: parsea config_rutas_ext_y_archivos.yaml, verifica
  YAML válido, cada modelo del orquestador tiene entrada, rutas relativas existen
Usa pytest. Todo debe pasar sin acceso a red.
```

---

### F11: Logging Estructurado — De print() a observabilidad

> **Tamaño:** M (~4d) · **Asignado:** `@vlandaetat`

**Archivos:**
- `core/logger.py` (nuevo)
- `core/orquestador.py` — migrar prints
- `procesamiento_datos_input/cache_tablas.py` — migrar prints

**Contexto:** Zero uso de `logging` en el proyecto. ~200+ `print()` con emojis. GUI `StdoutRedirector` depende de `print()`.

**Tareas:**
- [x] Crear `core/logger.py` con `setup_logger(nombre, fecha_proceso)`
- [x] Handler consola: formato legible con emojis (retrocompatible visualmente)
- [x] Handler archivo: `logs/{fecha}/modelos.jsonl` formato JSON (timestamp, level, modelo, mensaje)
- [x] Context manager o filtro para agregar `modelo` al contexto automáticamente
- [x] Migrar `print()` → `logger.xxx()` en `core/orquestador.py`
- [x] Migrar `print()` → `logger.xxx()` en `procesamiento_datos_input/cache_tablas.py`
- [x] Agregar handler/adapter para que la GUI `StdoutRedirector` siga funcionando
- [x] Verificar: `logs/20260227/modelos.jsonl` se crea con JSON válido
- [x] Verificar: consola mantiene formato legible
- [ ] Verificar: GUI sigue mostrando output
- [x] ⚠️ NO migrar los ~200 prints de modelos individuales en S1; solo `core/` y `procesamiento_datos_input/`
- [x] Interceptor de `print()` → JSONL: monkey-patch de `builtins.print` para capturar prints de modelos en JSONL

**Estrategia de captura de prints:**

| Enfoque | Estado | Cobertura | Detalle |
|---------|--------|-----------|---------|
| **Solución rápida:** interceptor `builtins.print` | ✅ Implementado | 100% de prints | Captura todos los `print()` en JSONL como `INFO`. Texto libre, no estructurado. Guard thread-local para evitar re-entrada. |
| **Solución robusta:** migrar `print()` → `logger.xxx()` por modelo | 📋 Mediano plazo | — | Permite niveles (WARNING/ERROR), campos extra, filtrado. ~200 prints en 10 módulos. Ejecutar gradualmente fuera de S1. |

**Preguntas resueltas:**
- [x] ❓ ¿JSON desde el inicio? → Sí, JSONL desde el inicio para consumo por Torre de Control (F01)
- [x] ❓ ¿Mantener emojis en handler consola? → Sí, `ConsoleFormatter` solo emite el mensaje tal cual
- [x] ❓ ¿Migrar solo `core/` y `procesamiento_datos_input/` en S1? → Sí + interceptor para cobertura inmediata

---

## S2 — Observabilidad Core (Mar 10 → Mar 21)

### F01: Torre de Control -- Dashboard Streamlit

> **Tamano:** L (~8d) -- **Asignado:** @vlandaetat
> **Depende de:** F11
> **Estado:** Parcialmente implementado como `dashboard/` (Quick-Wins DQW)

**Que:** Streamlit dashboard con estado/duracion/errores de todos los modelos

**Nota:** El dashboard ya existe como `dashboard/app.py` con 6 paginas (Home, Logs,
Comparacion, Benchmark, Parametros, Email Report). La "Torre de Control" original
(F01) se implemento como Dashboard Quick-Wins (DQW) durante S2 con nombre `dashboard/`
en vez de `torre_control/`. El scope de F01 se considera cubierto por DQW + las
mejoras incrementales en S2.

**Archivos:**
- `dashboard/app.py` -- entry point multi-pagina (`st.navigation`)
- `dashboard/pages/1_Home.py` -- Mission Control: metricas, alertas, logs
- `dashboard/pages/2_Logs.py` -- Explorador de logs JSONL
- `dashboard/pages/3_Comparacion.py` -- Comparacion outputs t vs t-1 (BQ)
- `dashboard/pages/4_Benchmark.py` -- Trending de performance por fase
- `dashboard/pages/5_Parametros.py` -- Diff de parametros entre fechas
- `dashboard/pages/6_Email.py` -- Preview + envio de reporte email
- `dashboard/utils/` -- bq_client.py, local_data.py, theme.py

**Tareas:**
- [x] Layout Streamlit multi-pagina con st.navigation
- [x] Home: KPIs, tabla de modelos, alertas, logs recientes
- [x] Logs: explorador con filtros por modelo/nivel
- [x] Comparacion: delta t vs t-1 por moneda desde BQ
- [x] Benchmark: trending de duracion por fase
- [x] Parametros: diff JSON entre fechas
- [x] Email: preview de comparacion + envio via Outlook COM
- [x] Alertas en expander colapsable por defecto
- [x] Fecha default salta fines de semana
- [ ] Auto-refresh cada N segundos (WIP)
- [ ] Autenticacion (si se despliega fuera de localhost)

---

### F12: Configuración Unificada — Un solo YAML

> **Tamaño:** M (~4d) · **Asignado:** `________`

**Qué:** Unificar 3+ fuentes de config en un solo YAML

**Archivos:**
- `config/modelos.yaml` (nuevo)
- `core/orquestador.py` — leer del YAML en vez de dict hardcoded
- `main.py` — generar `MODELO_A_TABLAS` desde YAML
- `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` — eliminar duplicación

**Contexto:** `MODELO_A_TABLAS` duplicado en 3 archivos. Dict hardcoded en orquestador con `nombre`, `modulo`, `orden`, `vuelta`, `activado`, `tiene_carga_gcp`, `tiene_carga_gcp_historica`.

**Tareas:**
- [ ] Diseñar schema de `config/modelos.yaml` (nombre, modulo, orden, vuelta, activado, tiene_carga_gcp, tablas_bigquery, rutas)
- [ ] Crear `config/modelos.yaml` con los 10 modelos
- [ ] Refactorizar `OrquestadorModelos.__init__()` para leer del YAML
- [ ] Refactorizar `main.py` → `MODELO_A_TABLAS` generado dinámicamente
- [ ] Eliminar `MODELO_A_TABLAS` hardcoded de `hist.py`
- [ ] Test: agregar modelo mock al YAML → orquestador lo detecta sin cambiar Python
- [ ] Test: `python main.py --listar` muestra todos los modelos del YAML
- [ ] Verificar que los 10 modelos originales siguen funcionando idéntico
- [ ] Eliminar dead code: `main()` duplicado en `orquestador.py`

**Preguntas por resolver:**
- [ ] ❓ ¿Mantener `config_rutas_ext_y_archivos.yaml` separado y referenciar, o fusionar?
- [ ] ❓ ¿El YAML es la única fuente de verdad para agregar modelos nuevos?
- [ ] ❓ ¿Auto-registro de módulos o YAML suficiente?

**Prompt sugerido:**
```
Crea config/modelos.yaml con estructura unificada por modelo: nombre, modulo,
orden, vuelta, activado, tiene_carga_gcp, tablas_bigquery (lista), rutas
(ref a config_rutas_ext_y_archivos.yaml o inline).
Refactoriza OrquestadorModelos.__init__() para leer del YAML.
Refactoriza main.py para generar MODELO_A_TABLAS desde el YAML.
Elimina duplicación en hist.py.
```

---

### F26: Sistema de Reportes Email Multi-Tipo + Dashboard Integration

> **Tamano:** M (~3d) -- **Asignado:** @vlandaetat
> **Rama:** `feature/email-report` (mergeado a `main`)

**Que:** Evolucionar `email_report.py` de reporte unico (primera vuelta) a sistema
multi-tipo con config YAML compartida e integracion con orquestador + dashboard Streamlit.

**Tipos de reporte:**
1. **Primera vuelta** -- amortizacion por moneda/producto (implementado)
2. **Segunda vuelta** -- misma estructura, tablas CMR/NMD/LC/Inversiones
3. **Chequeo interfaces** -- sumas amortizacion/interes + conteo registros por SISTEMA y MONEDA_ORIGEN

**Criterio UX:** Todas las etiquetas visibles usan fechas reales (ej: "2026-03-10 vs 2026-03-07"),
nunca "t" ni "t-1".

**Fases:**
- [x] Fase 1: Reestructuracion YAML + refactor base multi-tipo
- [ ] Fase 2: Reporte segunda vuelta
- [ ] Fase 3: Actualizacion run_diario.bat
- [ ] Fase 4: Integracion con orquestador (auto-send post-ejecucion)
- [ ] Fase 5: Reporte chequeo de interfaces (pendiente detalle)
- [x] Fase 6: Dashboard email page (`dashboard/pages/6_Email.py`)
  - Preview de comparacion con tabla resumen por modelo + delta%
  - Charts por modelo con eje Y escalado inteligente (Millones / Miles de MM)
  - Data card con valores exactos al costado de cada chart
  - Envio directo o apertura en Outlook
  - pythoncom CoInitialize/CoUninitialize para COM en threads Streamlit
- [ ] Fase 7: Auto-send inteligente (solo planificacion)

**Mejoras visuales aplicadas (Fase 6):**
- Colores: celeste (#90CAF9) para t-1, verde (#4CAF50) para t
- Delta% como anotacion centrada en el chart (verde alza, rojo baja)
- Eje Y auto-escalado: Millones si < 1B, Miles de MM si >= 1B
- xaxis type=category para evitar parsing de timestamps
- Layout email: chart (340px) + data card lateral con montos formateados
- Layout dashboard: chart izquierda + st.table derecha, un modelo por fila

**Plan detallado:** `docs/feats/email-report/PLAN.md`

---

### DQW: Dashboard Quick-Wins -- Streamlit Multi-Pagina

> **Tamano:** M (~3d) -- **Asignado:** @vlandaetat -- **Completado:** 2026-03-16
> **Rama:** `feature/dashboard-quick-wins` (mergeado a `main`)

**Que:** Dashboard Streamlit multi-pagina con 6 vistas para monitoreo y operacion diaria.

**Implementado:**
- [x] QW-0: App multi-pagina con `st.navigation()` (6 paginas)
- [x] QW-1: Home -- Mission Control con KPIs, tabla de modelos, alertas, logs
- [x] QW-2: Logs -- Explorador de logs JSONL con filtros
- [x] QW-3: Comparacion -- Delta t vs t-1 por moneda desde BQ historico
- [x] QW-4: Benchmark -- Trending de performance por fase
- [x] QW-5: Parametros -- Diff JSON entre fechas
- [x] Alertas en expander colapsable (UX fix)
- [x] Fecha default salta fines de semana (UX fix)

**Archivos creados/modificados:**
- `dashboard/app.py`, `dashboard/pages/1_Home.py` a `5_Parametros.py`
- `dashboard/utils/bq_client.py`, `local_data.py`, `theme.py`

---

### HF-ENCODING: Hotfix Encoding UTF-8

> **Tamano:** XS (~0.5d) -- **Asignado:** @vlandaetat -- **Completado:** 2026-03-16

**Que:** Fix `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90` al ejecutar
modelos de segunda vuelta en Windows (cp1252 default).

**Causa raiz:** 12 archivos Python abrian `config_rutas_ext_y_archivos.yaml` con
`open(..., 'r')` sin `encoding='utf-8'`, y el YAML contenia caracteres `<-` (antes `U+2190`)
y `--` (antes `U+2014 EM DASH`) que no existen en cp1252.

**Implementado:**
- [x] 10 archivos de modelos: `open(yaml)` con `encoding='utf-8'`
- [x] `cargador_modelos.py`, `cargar_output_modelos_bigquery_dly.py`: idem
- [x] `config_rutas_ext_y_archivos.yaml`: reemplazar flechas y em-dash por ASCII
- [x] `core/email_report.py`: limpiar simbolos no-ASCII
- [x] `.github/copilot-instructions.md`: agregar seccion `## Unicode / encoding`

---

## S3 — Validación & Alertas (Mar 24 → Abr 4)

### F03: Modo Fantasma — Validación VBA vs Python

> **Tamaño:** L (~8d) · **Asignado:** `________`
> **Depende de:** F15 ✅

**Qué:** Framework de comparación automática entre outputs VBA y Python (empezando por Inversiones)

**Archivos:**
- `tools/comparar_outputs.py` (nuevo)
- `RF_Modelo_Inversiones/tests/test_fantasma.py` (nuevo)

**Tareas:**
- [ ] Crear `tools/comparar_outputs.py` con clase `ComparadorOutputs`
- [ ] Leer dos Excel como DataFrames
- [ ] Comparar celda por celda con tolerancia abs y relativa configurable
- [ ] Generar reporte markdown: campos coinciden/difieren, diff abs/rel, resumen estadístico
- [ ] Crear `RF_Modelo_Inversiones/tests/test_fantasma.py` como test pytest
- [ ] Almacenar output VBA de referencia en `tests/fixtures/`
- [ ] Integrar como test de regresión ejecutable con `pytest`
- [ ] Documentar cómo correr validación fantasma

**Preguntas por resolver:**
- [ ] ❓ ¿Outputs VBA disponibles como archivos en red, o hay que ejecutar VBA?
- [ ] ❓ ¿Tolerancia por defecto? ¿Absoluta (±0.01) o relativa (±0.1%)?
- [ ] ❓ ¿Empezar solo con Inversiones o incluir segundo modelo?
- [ ] ❓ ¿Reporte HTML (visual) o markdown (versionable)?

**Prompt sugerido:**
```
Crea tools/comparar_outputs.py con clase ComparadorOutputs:
1. Lee dos Excel como DataFrames
2. Compara celda por celda con tolerancia abs y relativa configurable
3. Genera reporte markdown: columnas que coinciden, campos que difieren
   (valor esperado vs actual, diff abs/rel), resumen estadístico
Crea RF_Modelo_Inversiones/tests/test_fantasma.py como test pytest que
compare output Python vs output VBA de referencia en tests/fixtures/.
```

---

### F17: Parallel Smartness — Ejecución por vueltas

> **Tamaño:** M (~4d) · **Asignado:** `________`
> **Depende de:** F14 ✅

**Qué:** Ejecución en 2 fases (primera/segunda vuelta) con pre-carga de caché Access

**Archivos:**
- `core/orquestador.py` — `ejecutar_modelos_paralelo()` hoy ignora `vuelta`
- `procesamiento_datos_input/cache_tablas.py` — pre-carga `RF_BD_Gestion_RL`

**Contexto:** El campo `vuelta` (1 o 2) existe pero nunca se usa. `ThreadPoolExecutor` dispara todo simultáneamente. NMD y LC compiten por lock de Access.

**Tareas:**
- [ ] Separar modelos por `vuelta` en `ejecutar_modelos_paralelo()`
- [ ] Pre-cachear tablas Access compartidas via `cache_tablas.leer_tabla_con_cache()`
- [ ] Ejecutar primera vuelta en paralelo → esperar → segunda vuelta en paralelo
- [ ] Agregar opción `--secuencial` para debugging
- [ ] Test: NMD y LC no compiten por `RF_BD_Gestion_RL`
- [ ] Medir mejora de tiempo total vs ejecución actual

**Preguntas por resolver:**
- [ ] ❓ ¿Modelos de segunda vuelta dependen del output de primera vuelta, o solo comparten fuente Access?
- [ ] ❓ ¿Pre-cargar `RF_BD_Gestion_RL` completo es viable? ¿Tamaño?
- [ ] ❓ ¿Overhead de 2 fases secuenciales aceptable vs todo paralelo?

**Prompt sugerido:**
```
Modifica ejecutar_modelos_paralelo() en core/orquestador.py para:
1. Separar modelos por campo vuelta (1 y 2)
2. Antes de primera vuelta: pre-cachear tablas Access compartidas via
   cache_tablas.leer_tabla_con_cache()
3. Ejecutar primera vuelta en paralelo → esperar
4. Ejecutar segunda vuelta en paralelo
Agregar opción --secuencial para debugging.
```

---

### F09: Alertas Inteligentes — Detección de anomalías

> **Tamaño:** M (~4d) · **Asignado:** `________`
> **Depende de:** F11 ✅

**Qué:** Sanity checks post-ejecución: variación diaria, reconciliación, completitud

**Archivos:**
- `alertas/checks.py` (nuevo)
- `alertas/modelos.py` (nuevo)

**Tareas:**
- [ ] Crear `alertas/checks.py` con funciones:
  - [ ] `check_variacion_diaria(df_hoy, df_ayer, umbral_std=3)`
  - [ ] `check_completitud(df, columnas_criticas)`
  - [ ] `check_rango_valores(df, specs)`
- [ ] Crear `alertas/modelos.py` — aplicar checks post-ejecución por modelo
- [ ] Definir specs de columnas críticas por modelo (en YAML de F12)
- [ ] Integrar con logger de F11 (severidad: INFO, WARNING, CRITICAL)
- [ ] Integrar con Torre de Control de F01 (visualización de alertas)
- [ ] Test con datos simulados

**Preguntas por resolver:**
- [ ] ❓ ¿Hay baseline histórico para calcular desviaciones, o reglas fijas primero?
- [ ] ❓ ¿Alertas deben bloquear carga a BQ, o solo reportar?
- [ ] ❓ ¿Integración email/Teams/Slack, o solo log + dashboard?
- [ ] ❓ ¿Qué columnas son "críticas" por modelo?

**Prompt sugerido:**
```
Crea alertas/checks.py con funciones:
- check_variacion_diaria(df_hoy, df_ayer, umbral_std=3)
- check_completitud(df, columnas_criticas)
- check_rango_valores(df, specs)
Crea alertas/modelos.py que aplique checks post-ejecución por modelo usando
specs definidas en el YAML de configuración. Integrar con logger de F11.
```

---

## S4 — Datos Históricos & Legacy (Abr 7 → Abr 18)

### F19: Carga Modelos Old — Tablas legacy a BigQuery

> **Tamaño:** L (~8d) · **Asignado:** `________`
> **Ref:** `docs/feats/carga-modelos-old/PLAN.md`, `PLAN-v2.md`

**Qué:** Pipeline: Excel legacy DESARROLLO → DuckDB local → BigQuery

**Archivos:**
- `carga_modelos_gcp/cargar_modelos_old.py`
- `almacenamiento_local/duckdb_manager.py`
- `config/config_modelos_old.yaml`

**Contexto:** Rama `feat/carga-modelos-old` existe. Fases 1-2 parcialmente completadas. `duckdb` no está en requirements.txt.

**Tareas:**
- [ ] Sincronizar rama `feat/carga-modelos-old` con `main`
- [ ] Agregar `duckdb` a requirements.txt
- [ ] Implementar lectura de hojas DESARROLLO de Excel legacy
- [ ] Pipeline: Excel → pandas → DuckDB local → BigQuery
- [ ] Detección de duplicados en BQ
- [ ] Manejo de errores por modelo individual (try/except, no falla global)
- [ ] Soportar ejecución manual y automática desde orquestador
- [ ] Test con datos reales de al menos 2 modelos legacy

**Preguntas por resolver:**
- [ ] ❓ ¿Cuántos modelos legacy quedan? ¿Cuáles Excel?
- [ ] ❓ ¿Rama `feat/carga-modelos-old` al día con `main`? ¿Conflictos?
- [ ] ❓ ¿DuckDB es firme o se puede usar SQLite/parquet local?
- [ ] ❓ ¿Fases 1-2 en PLAN.md son código funcional o solo diseño?

---

### F18: Carga Históricos Pre-Python

> **Tamaño:** L (~8d) · **Asignado:** `________`
> **Ref:** `docs/feats/carga-historicos/PLAN.md`

**Qué:** Reconstruir serie histórica de outputs desde Access y respaldos Excel

**Archivos:**
- `carga_historicos/lector_access_historico.py` (nuevo)
- `carga_historicos/lector_excel_respaldos.py` (nuevo)
- `carga_historicos/cruzador_fuentes.py` (nuevo)
- `carga_historicos/exportador.py` (nuevo)

**Contexto:** Access vive en `Z:\RF_PROCESOS\RF_Modelos\`. Respaldos Excel en `Y:\RF_RESPALDO_DIARIO\RF_INPUTS`. Plan existe pero nothing implementado.

**Tareas:**
- [ ] Listar archivos `YYYYMMDD_RF_Modelos_Liquidez.accdb` en `Z:\...\RESPALDOS\`
- [ ] Implementar lector Access histórico → DataFrame con `fecha_respaldo`
- [ ] Listar respaldos Excel diarios en `Y:\RF_RESPALDO_DIARIO\RF_INPUTS`
- [ ] Implementar lector Excel respaldos → DataFrame
- [ ] Implementar cruzador: merge por fecha+modelo, reportar diferencias
- [ ] Implementar exportador: parquet / CSV / BigQuery
- [ ] Manejar fechas faltantes y datos erróneos sin crashear
- [ ] Reporte de cobertura: ¿qué fechas/modelos tienen datos completos?

**Preguntas por resolver:**
- [ ] ❓ ¿Rango de fechas target? ¿Desde cuándo existen respaldos?
- [ ] ❓ ¿Estructura de respaldos Access consistente entre fechas?
- [ ] ❓ ¿Qué hojas/columnas de los Excel contienen outputs de modelos?
- [ ] ❓ ¿Tolerancia de diferencia Access vs Excel? ¿95% match suficiente?

---

## S5 — UX & Playground (Abr 21 → May 9)

### F04: Scenario Playground — Análisis interactivo

> **Tamaño:** XL (~12d) · **Asignado:** `________`
> **Depende de:** F14 ✅, F11 ✅

**Qué:** Streamlit con sliders de parámetros para ver efecto en tiempo real (piloto: Prepago Consumo)

**Archivos:**
- `playground/app_prepago.py` (nuevo)
- `RF_Modelo_Prepago_Consumo/mr_prepago_consumo.py` — refactorizar firma

**Contexto:** `ejecutar_modelo()` hoy solo acepta `fecha`. Necesita `ejecutar_modelo(fecha, parametros=None, datos=None)`.

**Tareas:**
- [ ] Refactorizar `ejecutar_modelo()` de Prepago Consumo para aceptar `parametros=None, datos=None`
- [ ] Crear `playground/app_prepago.py` con Streamlit
- [ ] Sliders para PHI, factor SMM, tasa base
- [ ] Gráfico de flujos proyectados base vs stress
- [ ] Datos cargados desde caché parquet (sin red)
- [ ] Documentar patrón para extender a otros modelos

**Preguntas por resolver:**
- [ ] ❓ ¿Qué parámetros de Prepago Consumo son los más relevantes para variar?
- [ ] ❓ ¿Genera datos reales (escribe Excel) o solo visualiza sin side effects?
- [ ] ❓ ¿Accesible solo por devs o también analistas de negocio?

---

### F06: Linaje de Datos — Visualización de flujo

> **Tamaño:** L (~8d) · **Asignado:** `________`
> **Depende de:** F12 ✅

**Qué:** Grafo interactivo fuentes → modelos → outputs, generado desde YAML de config

**Archivos:**
- `tools/generar_linaje.py` (nuevo)
- `docs/desarrollo/linaje.md`

**Tareas:**
- [ ] Crear `tools/generar_linaje.py` que lea `config/modelos.yaml` (de F12)
- [ ] Generar diagrama Mermaid: fuentes → modelos → outputs
- [ ] Integrar en MkDocs
- [ ] Auto-actualización con cada cambio en YAML (pre-commit hook o build step)

**Preguntas por resolver:**
- [ ] ❓ ¿Mermaid integrado en MkDocs suficiente, o algo interactivo (D3)?
- [ ] ❓ ¿Actualización automática o manual?

---

## Backlog Estratégico (sin sprint asignado)

| ID | Feature | Prioridad | Tamaño | Notas |
|----|---------|-----------|--------|-------|
| F05 | Matadero de Access (SQL→Pandas) | Baja | L | Depende de cuántos modelos sigan en Access |
| F07 | Parámetros como Código (Excel→YAML) | Media | XL | Visión largo plazo; precursor: F20 |
| F08 | Copiloto Regulatorio (reportes CMF) | Baja | XXL | Depende de F01+F09 |
| F10 | Model API (FastAPI) | Baja | XXL | Depende de F11+F12 |
| F20 | Reestructura Parámetros (Excel→JSON) | Media | XL | Rama existe; considerar mover a S5 si hay capacidad |

---

## Grafo de Dependencias

```
F02 ──────────────────────────────────────→ F07, F20
F11 ──→ F01 ──→ F09
F11 ──→ F04
F12 ──→ F06
F14 ──→ F17
F14 ──→ F04
F15 ──→ F03
F16 (independiente)
F13 (independiente)
F18, F19 (independientes)
```

---

## Notas de Arquitectura

1. **`bfa_cl_utilidades`** es paquete externo/propietario usado en todo el proyecto pero no en requirements.txt — se instala por separado
2. **`vuelta` existe pero no se usa** — F17 implementará la ejecución por fases
3. **`MODELO_A_TABLAS` duplicado en 3 archivos** — F12 lo unificará
4. **Orquestador tiene `main()` duplicado** que es dead code — limpiar en F12
5. **GUI cubre solo 6 de 10 modelos** y no tiene funcionalidad GCP
6. **Cache solo cubre Access** — F14 lo extiende a CSVs de red

---

## Registro de Decisiones

| Fecha | Decisión | Contexto |
|-------|----------|----------|
| 2026-02-27 | F16 movido de S3 a S1 | Quick win (~10 líneas), fix crítico de idempotencia |
| 2026-02-27 | F09 movido de S2 a S3 | Descomprime S2 que estaba sobrecargado |
| 2026-02-27 | F18/F19 asignados a S4 nuevo | Urgencia de negocio para serie histórica completa |
| 2026-02-27 | F04/F06 movidos a S5 (3 semanas) | UX valioso pero no urgente; XL necesita buffer |
| 2026-02-27 | F02 completado | Snapshot de parámetros con shutil.copy2; aborta modelo si falla |
| 2026-02-27 | F16 completado | DELETE+INSERT siempre en históricos BQ; sin flag, idempotencia total |
| 2026-02-28 | F16 rediseñado | Cambio a flag --force-historico: por defecto omite si existe. Con flag: backup CSV + DELETE + INSERT + metadata JSON |
