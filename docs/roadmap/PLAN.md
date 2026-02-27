# Plan de Ejecución — Roadmap BFA-CL Modelos Diarios

> **Fuente de verdad del roadmap:** [`roadmap.yaml`](roadmap.yaml)
> **Última actualización:** 2026-02-27
> **Equipo:** Victor Landaeta (`@vlandaetat`), Rodrigo Muñoz (`@rmunozb`)

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
| **S1** | Feb 25 → Mar 7 | Quick Wins & Fundamentos | F02, F16, F14, F13, F15, F11 |
| **S2** | Mar 10 → Mar 21 | Observabilidad Core | F01, F12 |
| **S3** | Mar 24 → Abr 4 | Validación & Alertas | F03, F17, F09 |
| **S4** | Abr 7 → Abr 18 | Datos Históricos & Legacy | F18, F19 |
| **S5** | Abr 21 → May 9 | UX & Playground | F04, F06 |

---

## S1 — Quick Wins & Fundamentos (Feb 25 → Mar 7)

### F02: Máquina del Tiempo — Snapshots de parámetros

> **Tamaño:** XS (~0.5d) · **Asignado:** `________`

**Qué:** `shutil.copy` de Excel de parámetros antes de cada ejecución → `snapshots/{fecha}/{modelo}/`

**Archivos:**
- `core/orquestador.py` — agregar método `_snapshot_parametros()`
- Paths ya en `config/config_rutas_ext_y_archivos.yaml` bajo `excel_parametros_input`

**Tareas:**
- [ ] Implementar `_snapshot_parametros(modelo_key, fecha)` en `OrquestadorModelos`
- [ ] Leer rutas de `excel_parametros_input` del YAML por modelo
- [ ] Copiar con `shutil.copy2` a `snapshots/{YYYYMMDD}/{modelo_key}/`
- [ ] Manejar error de red sin bloquear ejecución (try/except + log)
- [ ] Llamar en `ejecutar_modelo()` justo antes de `modelo.ejecutar_modelo(fecha)`
- [ ] Verificar que funciona para `ml_inversiones` (parámetros en red UNC)
- [ ] Verificar overhead < 2s

**Preguntas por resolver:**
- [ ] ❓ ¿Incluir CSVs de interfaz en el snapshot, o solo Excel de parámetros?
- [ ] ❓ ¿Política de retención? ¿Borrar snapshots > N días automáticamente?
- [ ] ❓ Si la red no está disponible, ¿ejecutar sin snapshot o abortar?

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

### F16: Ejecución Idempotente — DELETE + INSERT en históricos

> **Tamaño:** S (~1d) · **Asignado:** `________`

**Qué:** Cambiar `consolidar_historico_bigquery()` de "skip si existe" a "DELETE + INSERT"

**Archivos:**
- `carga_modelos_gcp/cargar_output_modelos_bigquery_hist.py` — `verificar_datos_existentes()` y `consolidar_tabla()`

**Contexto:** Actualmente si `verificar_datos_existentes()` → `True`, imprime "SUSPENDIENDO inserción" y retorna. Si un INSERT parcial falla, no se puede corregir sin limpieza manual en BQ.

**Tareas:**
- [ ] Modificar `consolidar_tabla()` para hacer `DELETE FROM {tabla} WHERE fecha_proceso = '{fecha}'` antes de INSERT
- [ ] Loguear el DELETE realizado (filas eliminadas)
- [ ] Verificar que `fecha_proceso` es la columna correcta en todas las tablas históricas
- [ ] Test: ejecutar consolidación 2 veces → `COUNT(*)` idéntico
- [ ] Documentar el cambio de comportamiento

**Preguntas por resolver:**
- [ ] ❓ ¿La columna de fecha es siempre `fecha_proceso` o varía por modelo?
- [ ] ❓ ¿Flag `--force-historico` o comportamiento por defecto?
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

### F14: Cache de Primera Vuelta — CSV de red a parquet local

> **Tamaño:** S (~2d) · **Asignado:** `________`

**Qué:** Cachear `ProductosMercadoLiquidezGCP*.txt` de red como parquet local

**Archivos:**
- `procesamiento_datos_input/cache_tablas.py` — ya tiene TODOs explícitos (líneas 34-45)
- 6 modelos de primera vuelta que leen CSVs

**Contexto:** `cache_tablas.py` ya implementa cache parquet para Access. `--forzar-recarga` ya existe via `os.environ['CACHE_FORZAR_RECARGA']`.

**Tareas:**
- [ ] Implementar `leer_csv_con_cache(ruta_red, fecha, **read_csv_kwargs) -> DataFrame`
- [ ] Reusar patrón de `leer_tabla_con_cache()`: buscar parquet → si no existe, leer red → guardar parquet
- [ ] Respetar `CACHE_FORZAR_RECARGA` existente
- [ ] Modificar `mr_prepago_consumo.py` para usar `leer_csv_con_cache()`
- [ ] Modificar `mr_prepago_hipotecario.py`
- [ ] Modificar `ml_mora_consumo.py`
- [ ] Modificar `ml_mora_cae.py`
- [ ] Modificar `ml_mora_hipotecario.py`
- [ ] Modificar `ml_mora_comercial.py`
- [ ] Test: primera ejecución crea `.parquet` en `data/cache/`
- [ ] Test: segunda ejecución sin red funciona desde cache
- [ ] Test: `--forzar-recarga` re-lee de red

**Preguntas por resolver:**
- [ ] ❓ ¿El CSV cambia durante el día o es estable una vez publicado?
- [ ] ❓ ¿Hay modelos que filtren distinto el mismo CSV? ¿Cachear completo o filtrado?
- [ ] ❓ ¿El nombre del archivo incluye fecha o es siempre el mismo?

**Prompt sugerido:**
```
Extiende `procesamiento_datos_input/cache_tablas.py` con función
`leer_csv_con_cache(ruta_red: str, fecha: str, **read_csv_kwargs) -> pd.DataFrame`:
1. Busca `data/cache/{nombre_archivo}_{fecha}.parquet`
2. Si existe y CACHE_FORZAR_RECARGA no activo → retorna parquet
3. Si no → lee CSV de red, guarda como parquet, retorna
Después modifica los 6 modelos de primera vuelta para usar esta función.
```

---

### F13: Pre-flight Checks — Verificación de dependencias

> **Tamaño:** S (~2d) · **Asignado:** `________`

**Qué:** Health checks de rutas de red y bases Access ANTES de ejecutar modelos

**Archivos:**
- `core/preflight.py` (nuevo)
- `core/orquestador.py` — llamar pre-flight antes de ejecución

**Contexto:** Si la red está caída, el error aparece minutos después cuando `pyodbc.connect()` falla con timeout.

**Tareas:**
- [ ] Crear `core/preflight.py` con clase `PreflightChecker`
- [ ] Parsear YAML para obtener rutas de red y Access por modelo seleccionado
- [ ] Verificar accesibilidad con `os.path.exists()` + `os.access()`
- [ ] Para Access: `pyodbc.connect()` con timeout corto (~5s)
- [ ] Retornar `{modelo: {ok: bool, errores: [str]}}`
- [ ] Integrar en `orquestador.py` antes de `ejecutar_modelos_paralelo()`
- [ ] Permitir continuar solo con modelos que pasaron checks
- [ ] Manejar caso `ml_inversiones` (múltiples Access DBs en `ms_access_sources`)

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

### F01: Torre de Control — Dashboard Streamlit

> **Tamaño:** L (~8d) · **Asignado:** `________`
> **Depende de:** F11 ✅

**Qué:** Streamlit dashboard con estado/duración/errores de todos los modelos

**Archivos:**
- `torre_control/app.py` (nuevo)
- `torre_control/data.py` (nuevo)
- `requirements.txt` — agregar `streamlit`

**Tareas:**
- [ ] Agregar `streamlit` a requirements.txt
- [ ] Crear `torre_control/data.py` — parser de `logs/{fecha}/modelos.jsonl`
- [ ] Crear `torre_control/app.py` — layout Streamlit
- [ ] Sidebar: date picker para navegar días anteriores
- [ ] Tabla principal: Modelo, Estado (✅❌⏳), Duración, Hora inicio, Errores
- [ ] KPIs arriba: modelos ejecutados, duración total, tasa de éxito
- [ ] Manejar caso "sin ejecución registrada" para el día seleccionado
- [ ] Documentar cómo levantar: `streamlit run torre_control/app.py`
- [ ] Test con logs de 3+ días → datos correctos

**Preguntas por resolver:**
- [ ] ❓ ¿Corre local (localhost) o hay infra para deploy (GCP Cloud Run)?
- [ ] ❓ ¿Auto-refresh cada N segundos o refresh manual?
- [ ] ❓ ¿Incluir gráfico de tendencia de duración por modelo?
- [ ] ❓ ¿Necesita autenticación?

**Prompt sugerido:**
```
Crea torre_control/ con:
- torre_control/data.py: parsea logs/{fecha}/modelos.jsonl → DataFrames
- torre_control/app.py: Streamlit con sidebar (date picker), tabla principal
  (Modelo, Estado, Duración, Hora inicio, Errores), KPIs (modelos ejecutados,
  duración total, tasa de éxito). streamlit run torre_control/app.py
```

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
