# Changelog

Registro de cambios y actualizaciones del proyecto BFA-CL Modelos Diarios.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.12.0-dev] - 2026-04-06 - Sprint S3: Cache Parquet Compartido + Control Interfaces

### Agregado
- **Cache parquet compartido por tabla Access** (`cache_tablas.py`, `ml_nmd.py`, `ml_lc.py`, `mr_prepago_cmr.py`):
  NMD, LC y CMR ahora usan `leer_tabla_con_cache` con claves a nivel tabla
  (`RF_BD_Gestion_RL`, `RF_BD_Gestion_RM`) en lugar de claves aisladas por modelo.
  CMR reutiliza el parquet de inversiones (91K filas); NMD y LC comparten un unico parquet RL.
- **Proteccion contra cache envenenado** (`cache_tablas.py`): resultados de 0 filas
  no se guardan en parquet, evitando que una lectura fallida envenene el cache permanentemente.
- **Lookup copia local Access** (`cache_tablas.py`): ambas funciones de cache
  (`leer_tabla_con_cache`, `leer_multiples_tablas_con_cache`) buscan copia local
  via `_ACCESS_LOCAL_MAP` antes de leer desde ruta UNC de red.
- **Skip inteligente descarga Access** (`orquestador.py`): `_pre_ejecucion_segunda_vuelta`
  verifica si cache parquet esta completo antes de copiar archivos Access (~2 GB) desde red.
  `_CACHE_KEYS_MODELO_V2` define claves requeridas por modelo.
- **Herramienta precios historicos** (`tools/build_precios_db.py`): construye y sincroniza
  base SQLite de precios a partir de parquets de inversiones. Soporta roles reader/writer,
  sync por version con DB maestra en red, export CSV TCRC.
- **Config precios_db** (`config_rutas.py`, `config_rutas_ext_y_archivos.yaml`):
  nueva funcion `obtener_config_precios_db()` y bloque YAML con rutas de DB maestra,
  version, db local y CSV TCRC.
- **Control exploratorio de interfaces PML** (`core/control_interfaces.py`, F26 Fase 5):
  comparacion automatica de archivos ProductosMercadoLiquidez (GCP y CMR) entre t vs t-1.
  Sumas de AMORTIZACION e INTERES por grupo, delta% con umbrales WARNING/CRITICAL,
  reporte HTML via Outlook COM. CLI: `--control-interfaces [gcp|cmr|todos]`.
- **Plan tecnico control interfaces** (`docs/feats/control-interfaces/PLAN.md`)

### Corregido
- **Validacion fecha consolidar-historico** (`cargar_output_modelos_bigquery_hist.py`):
  verifica que la tabla diaria BigQuery contenga datos para la fecha solicitada
  antes de ejecutar INSERT en historico. Previene copia silenciosa de datos de
  otra fecha de proceso al partition equivocado.
- **Deteccion rutas ms_access_input** (`orquestador.py`): `_obtener_rutas_access_v2`
  ahora detecta tanto `ms_access_sources` (inversiones) como `ms_access_input` (NMD/LC/CMR).

## [1.11.0-dev] - 2026-03-17 - Sprint S2: Dashboard Email + Encoding Hotfix + Chart Redesign

### Agregado
- **Pagina Email en Dashboard (F26 Fase 6)** (`dashboard/pages/6_Email.py`): preview y envio de reportes email desde Streamlit
  - Tabla resumen por modelo con delta% por moneda (verde/rojo)
  - Charts individuales por modelo con eje Y escalado inteligente (Millones / Miles de MM)
  - Data card lateral con valores exactos, diferencia y variacion porcentual
  - Selector de tipo de reporte (primera/segunda vuelta), fecha, modo y destinatarios
  - Envio directo o apertura en Outlook para revision
  - Registrado en `dashboard/app.py` como 6a pagina

### Cambiado
- **`core/email_report.py`**: rediseno completo de charts y HTML del email
  - Charts individuales por modelo (antes: todos los modelos en 1 chart por moneda)
  - Colores: celeste (#90CAF9) t-1, verde (#4CAF50) t (antes: rojo/azul)
  - Eje Y escalado inteligente: auto-detecta Millones vs Miles de MM
  - Delta% como anotacion centrada en el chart (verde alza, rojo baja)
  - HTML: chart (340px) + data card lateral con montos formateados
  - Tabla resumen por modelo con delta% por moneda (antes: total amortizacion por moneda)
  - xaxis type=category para evitar timestamps con horas en eje X
  - pythoncom CoInitialize/CoUninitialize para COM en threads Streamlit
- **`dashboard/pages/1_Home.py`**: alertas en expander colapsable, fecha default salta fines de semana
- **`config/config_rutas_ext_y_archivos.yaml`**: destinatario default actualizado a riesgofinanciero@bancofalabella.cl

### Corregido
- **Hotfix encoding UTF-8** (14 archivos): `UnicodeDecodeError` al ejecutar modelos en Windows (cp1252)
  - 12 archivos Python: agregar `encoding='utf-8'` en `open()` de YAML
  - YAML: reemplazar caracteres no-ASCII (flechas, em-dash) por equivalentes ASCII
  - `core/email_report.py`: limpiar simbolos Unicode no compatibles con cp1252
  - `.github/copilot-instructions.md`: agregar seccion `## Unicode / encoding`

## [1.10.0-dev] - 2026-03-16 - Sprint S2: Reportes Email Multi-Tipo + Pre-flight Checks

### Agregado
- **Pre-flight Checks (F13)** (`core/preflight.py`): verificación de dependencias antes de ejecutar modelos
  - Checks de rutas de red, bases Access, Excel de parámetros y driver ODBC
  - Dataclasses `CheckResult` / `PreflightReport` para resultados estructurados
  - Deduplicación automática de rutas compartidas entre modelos
  - Integrado en `ejecutar_modelos_paralelo()` y `ejecutar_modelo_secuencial()`
  - Rama: `feat/F13-preflight-checks` (3e7889b), mergeado a `main`
- **Sistema de Reportes Email Multi-Tipo (F26)** (`core/email_report.py`): evolución a sistema multi-tipo
  - Config YAML con sección compartida + sub-secciones por tipo de reporte
  - Soporte para: primera vuelta, segunda vuelta, chequeo interfaces (WIP)
  - Criterio UX: etiquetas visibles siempre usan fechas reales, nunca "t"/"t-1"
  - Plan detallado en `docs/feats/email-report/PLAN.md`
  - Rama: `feature/email-report`

### Cambiado
- **`config/config_rutas_ext_y_archivos.yaml`**: `email_report:` reestructurado a config jerárquica multi-tipo

## [1.9.0-dev] - 2026-03-11 - Sprint S5: Handoff Practicante + Observabilidad Remota

### Agregado
- **Parametros JSON con fallback (F20)** (`tools/excel_a_json.py`, `procesamiento_datos_input/cargador_parametros.py`): migrar parametros de Excel a JSON
  - Herramienta de migracion `tools/excel_a_json.py` genera 9 archivos JSON con schema consistente
  - `cargador_parametros.py` reescrito: carga JSON primario con fallback a Excel
  - Todos los modelo integrados con nuevo sistema de carga
  - Rama: `feat/F20-parametros-json` (4afdd4d)
- **Reporte de ejecucion (F25)** (`core/reporte_ejecucion.py`): reportes estructurados post-ejecucion
  - Clase `ReporteEjecucion` con tracking por modelo (inicio/fin/duracion/status/error)
  - Benchmark historico contra promedio de ejecuciones anteriores (`data/benchmark/historial.jsonl`)
  - Alertas automaticas cuando duracion >50% sobre promedio historico
  - Output: JSON estructurado + Markdown legible en `reports/{YYYYMMDD}/`
  - Rama: `sprint/S5-optimizacion-pipeline` (e06d80c)
- **Sincronizacion BigQuery (F25)** (`core/sync_reportes.py`): reportes de ejecucion a BigQuery
  - Tabla `bfa_cl_prd_financial_risk_dly_proc_models.reportes_ejecucion` (auto-creada)
  - Fallback local en `reports/_pendientes_sync/` si falla la conexion
  - `sync_pendientes()` para reintentar uploads fallidos
  - Rama: `sprint/S5-optimizacion-pipeline` (e06d80c)
- **Health check de entorno** (`tools/check_env.py`): diagnostico de 14 puntos
  - Python, conda, dependencias, ODBC Access, GCP, YAML, carpetas, red, BigQuery
  - `--rapido` omite checks de red; `--json-only` para scripts
  - Integrado en `main.py` como `--check-env`
  - Compatible con cmd.exe (cp1252 safe, UTF-8 reconfigure)
  - Rama: `sprint/S5-optimizacion-pipeline` (16b35a8)
- **Scripts wrapper .bat** para practicante:
  - `setup_env.bat`: crea env conda + instala deps + wheel + health check
  - `run_diario.bat`: menu interactivo (fecha, vueltas, carga GCP, consolidar)
  - `check_env.bat`: wrapper para health check completo
  - Rama: `sprint/S5-optimizacion-pipeline` (91828f6)
- **Wheel vendorizado** (`vendor/bfa_cl_utilidades-1.0.4-py3-none-any.whl`): instalacion offline de bfa_cl_utilidades
  - Elimina dependencia de `Z:/RF_INSTALADORES/` para setup del practicante
  - Rama: `sprint/S5-optimizacion-pipeline` (fca5dbe)
- **Documentacion handoff** (`docs/guia/`):
  - `SETUP.md`: guia de instalacion paso a paso para practicante
  - `DAILY_WORKFLOW.md`: flujo de trabajo diario detallado
  - `TROUBLESHOOTING.md`: solucion de problemas comunes
  - `docs/feats/handoff-practicante/PLAN.md`: plan completo del feature

### Cambiado
- **`core/orquestador.py`**: integrado `ReporteEjecucion` — tracking automatico de inicio/fin/error por modelo
- **`main.py`**: generacion de reporte + sync a BigQuery post-ejecucion; flag `--check-env`
- **`README.md`**: actualizado con `.xlsx` (era `.xlsm`), nuevos modulos core, `.bat` scripts, `vendor/`, `reports/`, `tools/`
- **`docs/`**: actualizados index.md, guia/instalacion.md, guia/uso-basico.md, desarrollo/arquitectura.md, mkdocs.yml

## [1.8.0-dev] - 2026-03-10 - Sprint S5: Optimizacion de Rendimiento del Pipeline

### Agregado
- **Ejecución secuencial V1 (F21)** (`core/orquestador.py`): reemplazar `ThreadPoolExecutor` por loop `for` secuencial
  - Benchmark demostró speedup 1.01× con threading (GIL elimina beneficio para CPU-bound)
  - Reduce ~83 MB de consumo de RAM y simplifica debugging/logging
  - Rama: `feat/v1-secuencial` (239b62a)
- **WHERE exacto Access inversiones (F22)** (`RF_Modelo_Inversiones/io/data_sources.py`): filtrar `RF_base_Completa_Hist` con `WHERE Fec_Pro = fecha` en vez de cargar tabla completa
  - Reduce de ~308K filas (6 fechas) a ~51K filas (1 fecha)
  - Test `test_where_completa_hist.py` valida que output de cartera es idéntico con/sin WHERE
  - Verificado: BQ hist vs daily = MATCH PERFECTO (828 filas, schema idéntico)
  - Rama: `feat/where-access-inversiones` (1a04bf6, 6d760e8)
- **xlsxwriter para output Excel (F23)**: reemplazar openpyxl por xlsxwriter en los 10 modelos
  - Nuevo `core/excel_output.py` con `guardar_excel()` que agrupa múltiples hojas en una escritura
  - 9 modelos migrados de `ut.cargar_datos_xlsm()` (openpyxl) a `guardar_excel()` (xlsxwriter)
  - Inversiones: `engine='openpyxl'` → `engine='xlsxwriter'` en `excel_writer.py`
  - Confirmado: 10 archivos .xlsm con 0 macros VBA (vbaProject vacío en todos)
  - Benchmark: openpyxl 2.07s vs xlsxwriter 1.16s (~2× más rápido, 2 hojas × 5000 filas)
  - mora_consumo: 6 llamadas → 2 llamadas (1 por archivo output)
  - Rama: `feat/xlsxwriter-output` (7e74573)
- **Benchmark pipeline completo (F24)** (`sandbox/benchmark_pipeline_completo.py`): script de instrumentación de las 4 fases del pipeline
  - Rama: `feat/benchmark-pipeline` (60e7036)
- **Dashboard control histórico BQ** (`dashboard/app.py`): WIP Streamlit dashboard comparando SUM(AMORTIZACION) t vs t-1
  - Rama: `feat/dashboard-control-historico` (0b82bf6)

### Cambiado
- **Config YAML**: 10 extensiones de output `.xlsm` → `.xlsx` (sin macros VBA)
- **requirements.txt**: +`xlsxwriter==3.2.9`
- **Env conda**: `bfa-cl-modelos` → `bfa-cl-modelos-v2`

## [1.7.0-dev] - 2026-03-02 - Snapshots, Idempotencia y Documentación Integral

### Agregado
- **Snapshot de parámetros (F02)** (`core/orquestador.py`): copia automática de Excel de parámetros antes de cada ejecución
  - `_snapshot_parametros(modelo_key, fecha)` con `shutil.copy2` → `snapshots/{YYYYMMDD}/{modelo}/`
  - Lee rutas de `excel_parametros_input` del YAML de config por modelo
  - Aborta ejecución del modelo si la copia falla (`RuntimeError`)
  - Directorio `snapshots/` excluido de versionamiento (`.gitignore`)
- **Idempotencia históricos BQ (F16)**: flag `--force-historico` para re-inserción segura en tablas históricas BigQuery
  - `_exportar_backup_pre_delete()`: exporta registros existentes a CSV con timestamp + metadata JSON
  - `consolidar_historico_por_tabla(force=False)`: comportamiento dual — por defecto omite si datos existen (seguro); con `force=True` ejecuta backup → DELETE → INSERT → metadata post-INSERT
  - Backups en `backups_historicos/{YYYYMMDD}/{tabla}/` con `backups_historicos/` excluido de Git
  - Propagación de `force` a través de `consolidar_historico_bigquery()` y `consolidar_historico_gcp()`
  - `--force-historico` en `main.py` y `orquestador.py` (CLI)
  - Migración completa de `print()` → `logger` en `cargar_output_modelos_bigquery_hist.py`

### Mejorado
- **Documentación integral**: actualización de todos los archivos de documentación al estado actual del proyecto
  - `docs/roadmap/roadmap.yaml`: F02, F11, F14, F16 marcados como `completado` con fechas y asignaciones
  - `docs/roadmap/index.md`: Gantt con marcas `done`, badges de estado actualizados, F16 movido de S3 a S1, grafo de dependencias con colores diferenciados para completados
  - `README.md`: flag `--force-historico` en ejemplos CLI, `snapshots/` y `backups_historicos/` en estructura, `core/logger.py` visible
  - `docs/index.md`: `ml_inversiones` en tabla de modelos, estructura actualizada con `core/logger.py` y `logs/`

## [1.6.0-dev] - 2026-02-27 - Logging Estructurado, Roadmap y Documentación

### Agregado
- **Logging estructurado (F11)** (`core/logger.py`): sistema de logging con dos handlers — consola (formato legible con emojis) y archivo JSONL (`logs/{fecha}/modelos.jsonl`)
  - `setup_logging(fecha_proceso)` como punto de configuración centralizado
  - `contexto_modelo()` context manager para asociar logs al modelo correcto (thread-safe vía `contextvars`)
  - Monkey-patch de `builtins.print()` para captura completa de output en JSONL sin duplicar en consola
  - Prefijo `[modelo]` en consola para distinguir output en ejecución paralela (ej: `[prepago_consumo]`, `[mora_cae]`)
  - Compatible con `StdoutRedirector` de tkinter (GUI)
- **Copia local de interfaz PML (F14)**: interfaz PML con verificación pre/post para garantizar integridad de datos
- **Roadmap del proyecto** (`docs/roadmap/`): roadmap visual con Gantt y grafo de dependencias en Mermaid, fuente de verdad en `roadmap.yaml`
- **Plan de ejecución** (`docs/roadmap/PLAN.md`): plan de sprints S1–S5 con features F01–F20, asignaciones y dependencias
- **Workflow colaborativo** (`docs/roadmap/workflow.md`): guía de flujo GitLab con ramas, MR y convenciones
- **Documentación modelo Inversiones** (`docs/modelos/`): documentación técnica comprehensiva del pipeline de inversiones
- **Mermaid local** (`docs/overrides/`, `docs/javascripts/`): renderizado local de diagramas Mermaid para entornos con proxy corporativo
- **Benchmark** (`docs/desarrollo/`): análisis paralelo vs secuencial primera vuelta de modelos

### Mejorado
- **Orquestador** (`core/orquestador.py`): grupos de vueltas centralizados como metadata del orquestador (refactor)
- **Migración de `print()` a `logger`**: orquestador, cache_tablas y main.py migrados al nuevo sistema de logging
- **Dependencias** (`requirements.txt`): actualizado con `pip freeze` del ambiente `bfa-cl-modelos`

### Corregido
- **Modelo Inversiones**: `genera_tabla_RF_base_Completa_Hist` movido de `dev/helpers` a `io/data_sources` (ubicación correcta)
- **Gitignore**: `site/` y artefactos de build excluidos del versionamiento

## [1.5.0-dev] - 2026-02-23 - Modelo Inversiones: Pipeline completo + Carga GCP

### Agregado
- **Modelo Inversiones (`RF_Modelo_Inversiones/ml_inversiones.py`)**: Reescritura completa como orquestador de pipeline modular
- **Pipeline modular** en `RF_Modelo_Inversiones/pipeline/`: `tabla_final.py`, `validaciones.py`, `excels.py`
- **Capa de I/O** en `RF_Modelo_Inversiones/io/`: `data_sources.py`, `paths.py`, `writers.py`
- **Caché compartido de tablas Access** (`procesamiento_datos_input/cache_tablas.py`): lectura con `pyodbc` directo, 3 reintentos con backoff exponencial, sin dependencia de `bfa_cl_utilidades`
- **Tabla BQ daily** `report_ml_inversiones_dly` (32 columnas, WRITE_TRUNCATE)
- **Tabla BQ histórica** `report_ml_inversiones_hist` (32 columnas, PARTITION BY FECHA_PROCESO) — creada con DDL manual documentado en `RF_Modelo_Inversiones/dev/GCP_TABLAS_BIGQUERY_SETUP.md`

### Mejorado
- **Cargador GCP daily** (`cargar_output_modelos_bigquery_dly.py`): normalización de columnas con espacios → guiones bajos (9 mapeos), `format='mixed'` para fechas, `pd.to_numeric(errors='coerce')` para campos con strings no numéricos
- **Lector Access**: Reemplazo de `bfa_cl_utilidades.ejecutar_consulta_access` por `pyodbc` directo con reintentos (soluciona bloqueos concurrentes)

### Documentación
- `RF_Modelo_Inversiones/dev/GCP_TABLAS_BIGQUERY_SETUP.md`: Registro de auditoría con DDL, scripts de prueba y resultados de carga

## [1.4.0-dev] - 2026-02-03 - Incorporación del Modelo Línea de Crédito

### Agregado
- **Modelo de Línea de Crédito (LC)**: Nuevo modelo `RF_Modelo_Linea_de_Credito/ml_lc.py` implementado
- **Funcionalidades del modelo LC**:
  - Carga de datos de balance desde base de datos de gestión para líneas de crédito
  - Cálculo de submodelo dinamico para factores estacionales mensuales y bisemanales
  - Separación automática de flujos de ingreso (ACT) y egreso (PAS)
  - Soporte para producto LC_CLP (Línea de Crédito en CLP)
- **Plantilla Excel**: `ml_lc.xlsm` para cálculos y análisis del modelo
- **Parámetros configurables**: Factores GAMMA_1, DELTA_1, GAMMA_2, DELTA_2, DECAY_RATE y DECAY_RATE_ACURRACY
- **Validación de datos**: Verificación completa de datos iniciales y parámetros
- **Documentación técnica completa**: Docstrings detallados para todas las funciones principales

### Mejorado
- **Arquitectura del sistema**: Mantenimiento de la interfaz unificada `ejecutar_modelo(fecha_proceso) -> bool`
- **Documentación del proyecto**: README.md actualizado con estructura y descripción del modelo LC

### Modificado
- **Estructura del proyecto**: Incorporada carpeta `RF_Modelo_Linea_de_Credito/` con implementación completa
- **Lista de modelos consolidados**: Actualizada para incluir RF_Modelo_Linea_de_Credito como el 9no modelo del sistema

## [1.3.0-dev] - 2026-01-03 - Incorporación del Modelo NMD

### Agregado
- **Modelo de No Maduración de Depósitos (NMD)**: Nuevo modelo `RF_Modelo_NMD/ml_nmd.py` implementado
- **Funcionalidades del modelo NMD**:
  - Carga de datos de balance desde base de datos de gestión
  - Procesamiento de datos contractuales DAP con información detallada de flujos
  - Cálculo de flujos con decay rate para productos de depósitos
  - Aplicación de ajustes normativos de primera banda (25%)
  - Ajustes especiales DAP para primeros 90 días con el maximo entre el dato contractual y del modelo.
  - Soporte para múltiples productos: DAP (CLP, CLF, USD), Cuentas Corrientes, Cuentas Vista, Cuentas de Ahorro
- **Plantilla Excel**: `ml_nmd_cc.xlsm` para cálculos y análisis del modelo
- **Parámetros configurables**: Factores de decay rate y parámetros de core vigente
- **Validación de datos**: Verificación completa de datos iniciales y parámetros
- **Documentación técnica completa**: Docstrings detallados para todas las funciones principales

### Mejorado
- **Arquitectura del sistema**: Mantenimiento de la interfaz unificada `ejecutar_modelo(fecha_proceso) -> bool`
- **Documentación del proyecto**: README.md actualizado con estructura y descripción del modelo NMD

### Modificado
- **Estructura del proyecto**: Incorporada carpeta `RF_Modelo_NMD/` con implementación completa
- **Lista de modelos consolidados**: Actualizada para incluir RF_Modelo_NMD como el 8vo modelo del sistema

## [1.2.0-dev] - 2025-12-29 - Mejoras en Documentación y Consolidación de Funciones

### Mejorado
- **Documentación de funciones**: Docstrings comprehensivos implementados para `calcular_flujos_estimados_mora()` en todos los modelos de mora
- **Estándares de documentación**: Documentación técnica unificada con especificaciones detalladas de parámetros, valores de retorno y notas técnicas
- **Claridad funcional**: Explicaciones detalladas del propósito y funcionamiento de las funciones de cálculo de flujos

### Agregado
- **Documentación técnica completa**: 
  - Especificación detallada de `calcular_flujos_estimados_mora()`


### Modificado
- **Función consolidada**: `calcular_flujos_estimados_mora()` ahora procesa amortización e interés simultáneamente
- **Eficiencia mejorada**: Eliminación de duplicación de código mediante consolidación funcional



## [1.1.0-dev] - 2025-12-19 - Consolidación Arquitectónica

### Modificado
- **Consolidación de interfaz de modelos**: Todos los modelos ahora implementan una función `ejecutar_modelo(fecha_proceso) -> bool` unificada
- **Simplificación del orquestador**: Eliminado código de compatibilidad hacia atrás, ahora usa directamente la interfaz unificada
- **Estandarización de manejo de errores**: Patrón uniforme de captura y reporte de errores en todos los modelos
- **Validación consistente de datos**: Verificación estándar de datos vacíos en todos los modelos
- **Optimización de rendimiento**: Eliminación de verificaciones dinámicas en tiempo de ejecución

### Agregado
- **Interfaz unificada**: Función `ejecutar_modelo()` implementada en los 7 modelos del sistema
- **Documentación de funciones**: Docstrings consistentes para todas las funciones ejecutar_modelo
- **Manejo de retorno estándar**: Todos los modelos retornan `True`/`False` para indicar éxito/fallo

### Mejorado
- **Mantenibilidad del código**: Estructura consistente facilita el mantenimiento y debugging
- **Integración con orquestador**: Flujo de ejecución más predecible y eficiente
- **Escalabilidad**: Arquitectura preparada para agregar nuevos modelos fácilmente

#### Modelos Consolidados
- ✅ **RF_Modelo_Mora_Consumo**: `ml_mora_consumo.py`
- ✅ **RF_Modelo_Mora_CAE**: `ml_mora_cae.py`  
- ✅ **RF_Modelo_Mora_Comercial**: `ml_mora_comercial.py`
- ✅ **RF_Modelo_Mora_Hipotecario**: `ml_mora_hipotecario.py`
- ✅ **RF_Modelo_Prepago_CMR**: `mr_prepago_cmr.py`
- ✅ **RF_Modelo_Prepago_Consumo**: `mr_prepago_consumo.py`
- ✅ **RF_Modelo_Prepago_Hipotecario**: `mr_prepago_hipotecario.py`
- ✅ **RF_Modelo_NMD**: `ml_nmd.py`
- ✅ **RF_Modelo_Linea_de_Credito**: `ml_lc.py`

## [1.0.0-dev] - 2025-12-17 - Estado Inicial (En Desarrollo)

> ⚠️ **Proyecto en Desarrollo Activo**: Este sistema se encuentra actualmente en fase de desarrollo y mejora continua. Las funcionalidades pueden estar sujetas a cambios y optimizaciones.

### Agregado
- **Sistema completo de modelos de riesgo financiero** implementado
- **Orquestador principal** (`core/orquestador.py`) para coordinar ejecución de modelos
- **Interfaz de línea de comandos** con múltiples opciones de ejecución
- **Interfaz gráfica (GUI)** para operación visual del sistema
- **7 Modelos de Machine Learning** implementados:
  - **Modelos de Mora**: CAE, Comercial, Consumo, Hipotecario
  - **Modelos de Prepago**: CMR, Consumo, Hipotecario
- **Integración completa con Google Cloud Platform**:
  - Carga automática a BigQuery (diaria e histórica)
  - Credenciales y autenticación configuradas
- **Sistema de configuración centralizado**:
  - Archivo YAML para rutas externas (`config/config_rutas_ext_y_archivos.yaml`)
  - Módulo de configuración Python (`config/config_rutas.py`)
- **Plantillas Excel** para cada modelo con cálculos específicos
- **Notebooks de desarrollo** (Jupyter) para modelos de prepago
- **Directorios de parámetros** individuales para cada modelo
- **Historial de ejecuciones** para modelos de prepago
- **Archivo principal** (`main.py`) con funcionalidades:
  - Ejecución individual o masiva de modelos
  - Modo solo carga a GCP
  - Listado de modelos disponibles
  - Interfaz gráfica y modo consola
- **Documentación completa del proyecto**:
  - README.md con estructura detallada
  - Instrucciones de uso y configuración
  - Descripción de arquitectura del sistema
- **Configuración de seguridad**:
  - `.gitignore` para proteger credenciales
  - Exclusión de archivos temporales y sensibles
- **Estructura de documentación** (`docs/`) con changelog

### Características del Sistema
- **Ejecución paralela** de múltiples modelos
- **Procesamiento por lotes** de datos financieros
- **Carga automática** de resultados a BigQuery
- **Interfaz dual**: GUI y línea de comandos
- **Configuración flexible** por modelo
- **Integración con librería BFA-CL Utilidades**
- **Soporte para múltiples productos financieros**:
  - Créditos de consumo, comerciales e hipotecarios
  - Créditos automotriz empresas (CAE)
  - Tarjetas de crédito CMR

### Arquitectura Implementada
- **Patrón Orquestador** para coordinación de procesos
- **Separación de responsabilidades** por módulos
- **Configuración centralizada** y parametrizable
- **Integración cloud-native** con GCP
- **Interfaz de usuario modular** (GUI + CLI)

---

## Formato de Entradas

### [Versión] - YYYY-MM-DD

#### Agregado
- Nuevas funcionalidades y características

#### Modificado  
- Cambios en funcionalidades existentes

#### Corregido
- Corrección de bugs y errores

#### Eliminado
- Funcionalidades removidas

#### Seguridad
- Mejoras de seguridad y vulnerabilidades corregidas

---

## Notas

- **Agregado** para nuevas funcionalidades
- **Modificado** para cambios en funcionalidades existentes
- **Deprecated** para funcionalidades que serán removidas pronto
- **Eliminado** para funcionalidades removidas
- **Corregido** para cualquier corrección de bugs
- **Seguridad** en caso de vulnerabilidades

### Ejemplos de entradas:

```markdown
## [1.0.0] - 2025-12-17

### Agregado
- Nuevo modelo ML Mora CAE implementado
- Integración con BigQuery para carga automática
- Interfaz gráfica (GUI) para operación del sistema

### Modificado
- Optimizado rendimiento del orquestador principal
- Mejorada validación de parámetros en modelos de prepago

### Corregido
- Error en carga de configuración YAML
- Bug en procesamiento de fechas en modelo hipotecario

### Seguridad
- Implementadas credenciales encriptadas para GCP
- Agregada validación de acceso a recursos sensibles
```