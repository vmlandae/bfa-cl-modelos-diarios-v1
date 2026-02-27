# Changelog

Registro de cambios y actualizaciones del proyecto BFA-CL Modelos Diarios.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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