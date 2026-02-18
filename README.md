# BFA-CL Modelos Diarios

Sistema integral para la ejecución diaria de modelos de riesgo financiero en Banco Falabella Chile.

## Descripción

Este proyecto contiene la implementación de múltiples modelos de riesgo financiero que se ejecutan de forma automatizada:

### Modelos de Mora
- **ML Mora CAE**
- **ML Mora Comercial**
- **ML Mora Consumo**: Incluye Subproductos
- **ML Mora Hipotecario**: 

### Modelos de Prepago
- **MR Prepago CMR**
- **MR Prepago Consumo**
- **MR Prepago Hipotecario**

### Modelos de No Maduración de Depósitos (NMD)
- **ML NMD**: Modelado de flujos para productos de depósitos (DAP, Cuentas Corrientes, Cuentas Vista, Cuentas de Ahorro)

### Modelos de Línea de Crédito
- **ML LC**: Modelado de flujos para Líneas de Crédito. Considera dinamicas intrames y un decaimiento exponencial.

### Modelos de Inversiones
- **ML Inversiones**: Pipeline modular para modelado de inversiones con capa de I/O, validaciones y generación de excels.

### Modelos de Tarjeta de Credito CMR
- **ML TC CMR**: Modelado de flujos para Tarjeta de Credito CMR.

Los modelos están diseñados para procesar datos en lotes, generar predicciones y cargar los resultados a BigQuery para su posterior análisis y reporting.

## Estructura del Proyecto

### 📁 Directorio Raíz
```
main.py                          # Punto de entrada principal de la aplicación
setup_env.bat                    # Instalación automática del entorno (practicante)
run_diario.bat                   # Ejecución diaria interactiva
check_env.bat                    # Verificación de entorno
requirements.txt                 # Dependencias Python (pip freeze)
```

### 📁 Configuración y Core
```
config/                          # Configuraciones del sistema
├── config_rutas_ext_y_archivos.yaml  # Rutas externas y archivos de configuración
├── config_rutas.py              # Configuración de rutas del sistema
└── __init__.py

core/                           # Nucleo del sistema
├── orquestador.py              # Orquestador principal de procesos
├── logger.py                   # Logging estructurado (JSONL + consola)
├── excel_output.py             # Escritura Excel con xlsxwriter (F23)
├── email_report.py             # Reportes email multi-tipo via Outlook COM (F26)
├── control_interfaces.py       # Control exploratorio interfaces PML GCP/CMR (F26 Fase 5)
├── reporte_ejecucion.py        # Reportes de ejecucion + benchmark (F25)
├── sync_reportes.py            # Sincronizacion de reportes a BigQuery (F25)
└── __init__.py

credenciales/                   # Credenciales de acceso (no versionado)
└── bfa-cl-trade-price-report-dev-9d137fc23b7f.json
```

### 📁 Módulos de Carga de Datos
```
carga_modelos_gcp/              # Módulos para carga a Google Cloud Platform
├── cargar_output_modelos_bigquery_dly.py   # Carga diaria a BigQuery
├── cargar_output_modelos_bigquery_hist.py  # Carga histórica a BigQuery
└── __init__.py
```

### 📁 Interfaz de Usuario
```
gui/                            # Interfaz gráfica de usuario
├── controladores.py            # Controladores de la GUI
├── interfaz.py                 # Definición de la interfaz
└── __init__.py
```

### 📁 Modelos

#### Modelos de Mora
```
RF_Modelo_Mora_CAE/             # Modelo de mora para CAE (Crédito Automotriz Empresas)
├── ml_mora_cae.py              # Implementación del modelo
├── ml_mora_cae_cc.xlsx         # Output Excel
└── parametros/                 # Parámetros JSON + Excel

RF_Modelo_Mora_Comercial/       # Modelo de mora para créditos comerciales
├── ml_mora_comercial.py        # Implementación del modelo
├── ml_mora_comercial_cc.xlsx   # Output Excel
└── parametros/                 # Parámetros JSON + Excel

RF_Modelo_Mora_Consumo/         # Modelo de mora para créditos de consumo
├── ml_mora_consumo.py          # Implementación del modelo
├── ml_mora_consumo_cc.xlsx     # Output Excel
├── ml_mora_renegociado_cc.xlsx # Output renegociados
└── parametros/                 # Parámetros JSON + Excel

RF_Modelo_Mora_Hipotecario/     # Modelo de mora para créditos hipotecarios
├── ml_mora_hipotecario.py      # Implementación del modelo
├── ml_mora_hipotecario_cc.xlsx # Output Excel
└── parametros/                 # Parámetros JSON + Excel
```

#### Modelos de Prepago
```
RF_Modelo_Prepago_CMR/          # Modelo de prepago para tarjetas CMR
├── mr_prepago_cmr.py           # Implementación del modelo
├── mr_prepago_cmr.xlsx         # Output Excel
└── parametros/                 # Parámetros JSON + Excel

RF_Modelo_Prepago_Consumo/      # Modelo de prepago para créditos de consumo
├── mr_prepago_consumo.py       # Implementación del modelo
├── mr_prepago_consumo.xlsx     # Output Excel
└── parametros/                 # Parámetros JSON + Excel

RF_Modelo_Prepago_Hipotecario/  # Modelo de prepago para créditos hipotecarios
├── mr_prepago_hipotecario.py   # Implementación del modelo
├── mr_prepago_hipotecario.xlsx # Output Excel
└── parametros/                 # Parámetros JSON + Excel
```

#### Modelos de No Maduración de Depósitos (NMD)
```
RF_Modelo_NMD/                  # Modelo de no maduración para productos de depósitos
├── ml_nmd.py                   # Implementación del modelo
├── ml_nmd_cc.xlsx             # Output Excel
└── parametros/                 # Parámetros JSON + Excel
```

#### Modelos de Línea de Crédito
```
RF_Modelo_Linea_de_Credito/     # Modelo de línea de crédito
├── ml_lc.py                    # Implementación del modelo
├── ml_lc.xlsx                  # Output Excel
└── parametros/                 # Parámetros JSON + Excel (GAMMA, DELTA, DECAY_RATE)
```

#### Modelos de Inversiones
```
RF_Modelo_Inversiones/          # Modelo de inversiones (pipeline modular)
├── ml_inversiones.py           # Orquestador del pipeline
├── run_validacion.py           # Script de validación de output
├── config/                     # Configuración específica del modelo
├── io/                         # Capa de I/O (data_sources, paths, writers)
├── pipeline/                   # Pipeline modular (tabla_final, validaciones, excels)
├── parametros/                 # Parámetros específicos del modelo
├── tests/                      # Tests unitarios
└── dev/                        # Scripts de desarrollo y documentación GCP
```

### 📁 Datos, Reportes y Logs
```
logs/                           # Logs estructurados por fecha
└── {YYYYMMDD}/modelos.jsonl     # JSONL con contexto modelo/fecha

reports/                        # Reportes de ejecución (F25)
├── {YYYYMMDD}/reporte_*.json    # Reporte estructurado
├── {YYYYMMDD}/reporte_*.md      # Reporte legible
├── health_check.json           # Último diagnóstico de entorno
└── _pendientes_sync/           # Reportes pendientes de sync a BQ

data/
├── cache/                      # Caché parquet de tablas Access
└── benchmark/historial.jsonl   # Historial de benchmark de ejecuciones

snapshots/                      # Snapshots de parámetros (F02)
└── {YYYYMMDD}/{modelo}/         # Copia de Excel antes de cada ejecución

backups_historicos/             # Backups pre-DELETE de históricos BQ (F16)
└── {YYYYMMDD}/{tabla}/          # CSV + metadata JSON

vendor/                         # Dependencia offline
└── bfa_cl_utilidades-1.0.4-py3-none-any.whl
```

### Dashboard de Monitoreo
```
dashboard/                      # Dashboard Streamlit multi-pagina
├── app.py                      # Entry point (st.navigation)
├── pages/                      # Paginas del dashboard
│   ├── 1_Home.py               # Mission Control -- KPIs, alertas, logs
│   ├── 2_Logs.py               # Explorador de logs JSONL con filtros
│   ├── 3_Comparacion.py        # Comparacion outputs t vs t-1 (BQ hist)
│   ├── 4_Benchmark.py          # Trending de performance por fase
│   ├── 5_Parametros.py         # Diff de parametros entre fechas
│   └── 6_Email.py              # Preview + envio de reporte email
└── utils/                      # Utilidades compartidas
    ├── bq_client.py            # Cliente BQ cacheado
    ├── local_data.py           # Acceso a datos locales
    └── theme.py                # Constantes de estilo y modelos canonicos
```

#### Modelos de Tarjeta de Crédito CMR
```
RF_Modelo_TC_CMR/               # Modelo de tarjeta de crédito CMR
├── ml_tc_cmr.py                # Implementación del modelo
├── ml_tc_cmr.xlsm              # Plantilla Excel para cálculos
└── parametros/                 # Parámetros específicos del modelo
```

### 📁 Documentación
```
docs/                           # Documentacion del proyecto (MkDocs)
├── CHANGELOG.md                # Registro de cambios
├── roadmap/                    # Roadmap visual, plan de sprints y workflow
├── feats/dashboard-quick-wins/ # Brainstorm y spec del dashboard
├── feats/control-interfaces/   # Plan tecnico control interfaces PML (F26 Fase 5)
├── modelos/                    # Documentacion tecnica de cada modelo
├── guia/                       # Guias de uso, instalacion y troubleshooting
└── desarrollo/                 # Benchmarks y notas de desarrollo

tools/                          # Scripts de utilidad
├── check_env.py                # Health check del entorno (14 verificaciones)
├── test_gcp_permisos.py        # Diagnostico de permisos GCP
├── build_precios_db.py         # Construccion/sync base SQLite precios historicos
└── excel_a_json.py             # Migracion Excel -> JSON de parametros
```

## Arquitectura del Sistema

### Interfaz Unificada de Modelos
Todos los modelos implementan una interfaz consistente a través de la función `ejecutar_modelo(fecha_proceso) -> bool`, que:
- ✅ Encapsula toda la lógica de procesamiento del modelo
- ✅ Proporciona manejo unificado de errores
- ✅ Retorna un booleano indicando éxito/fallo
- ✅ Incluye validación consistente de datos de entrada
- ✅ Facilita la integración con el orquestador

### Estándares de Documentación
Los modelos implementan estándares avanzados de documentación técnica:
- ✅ **Docstrings comprehensivos**: Documentación detallada de funciones con especificaciones técnicas
- ✅ **Parámetros especificados**: Descripción completa de tipos de datos, formatos y restricciones
- ✅ **Valores de retorno documentados**: Estructura y contenido de DataFrames resultado claramente especificados
- ✅ **Notas técnicas**: Explicaciones de algoritmos, matrices de transición y factores de ajuste
- ✅ **Ejemplos de uso**: Código de ejemplo con parámetros reales para facilitar implementación


### Logging Estructurado
El sistema implementa logging dual a través de `core/logger.py`:
- **Consola**: formato legible con emojis y prefijo `[modelo]` para ejecución paralela
- **Archivo**: JSONL estructurado en `logs/{fecha}/modelos.jsonl` para análisis posterior
- **Compatibilidad**: funciona tanto en modo CLI como en la GUI (tkinter)

### Flujo Principal
1. **Orquestación**: El `orquestador.py` coordina la ejecución de todos los modelos
2. **Modelos**: Cada modelo procesa sus datos específicos y genera predicciones usando `ejecutar_modelo()`
3. **Logging**: Cada ejecución genera logs estructurados en JSONL con contexto del modelo
4. **Carga a GCP**: Los resultados se cargan automáticamente a BigQuery
5. **Interfaz**: La GUI permite monitorear y controlar las ejecuciones

### Componentes Clave
- **Orquestador**: Maneja la secuencia de ejecución y dependencias entre modelos
- **Modelos ML**: Implementaciones independientes con interfaz unificada `ejecutar_modelo()`
- **Configuración**: Sistema centralizado de configuración de rutas y parámetros
- **Carga GCP**: Módulos especializados para la integración con Google Cloud Platform

## Requisitos

- Python 3.11+ (entorno conda `bfa-cl-modelos-v2`)
- Anaconda o Miniconda
- Microsoft Access Database Engine 2016 (64-bit)
- Acceso VPN a red interna (para `\\vmdvorak`)
- Credenciales GCP (`credenciales/*.json`)
- `bfa_cl_utilidades` 1.0.4 (incluido en `vendor/` como `.whl`)

## Uso

### Opciones de Ejecución

El sistema ofrece múltiples modos de operación a través de la línea de comandos y interfaz gráfica.

#### Listar Modelos Disponibles
```bash
python main.py --listar
```

#### Ejecutar Modelos Específicos
```bash
# Ejecutar un modelo específico
python main.py --fecha 2025-11-28 --modelos mr_prepago_consumo

# Ejecutar múltiples modelos
python main.py --fecha 2025-11-28 --modelos mr_prepago_consumo ml_mora_cae

# Ejecutar todos los modelos disponibles
python main.py --fecha 2025-11-28 --modelos todos
```

#### Ejecutar y Cargar a BigQuery
```bash
# Ejecutar modelo y cargar automáticamente a BigQuery
python main.py --fecha 2025-11-28 --modelos mr_prepago_consumo --cargar-gcp

# Ejecutar todos los modelos y cargar a BigQuery
python main.py --fecha 2025-11-28 --modelos todos --cargar-gcp

# Ejecutar, cargar y forzar re-inserción en históricos (DELETE+INSERT)
python main.py --fecha 2025-11-28 --modelos todos --cargar-gcp --force-historico
```

#### Solo Carga a BigQuery (sin ejecutar modelos)
```bash
# Cargar modelos específicos a BigQuery
python main.py --fecha 2025-11-28 --solo-carga-gcp mr_prepago_consumo mr_prepago_hipotecario

# Cargar todos los modelos disponibles a BigQuery
python main.py --fecha 2025-11-28 --solo-carga-gcp todos
```

### Parámetros Principales

- `--fecha`: Fecha de ejecución en formato YYYY-MM-DD (requerido en modo consola)
- `--modelos`: Lista de modelos a ejecutar (usar nombres específicos o "todos")
- `--cargar-gcp`: Cargar resultados a BigQuery después de ejecutar
- `--solo-carga-gcp`: Solo cargar a BigQuery sin ejecutar modelos
- `--force-historico`: Forzar re-inserción en tablas históricas (DELETE+INSERT con backup CSV)
- `--listar`: Mostrar modelos disponibles y su estado

### Ejecucion de Modelos Individuales
Cada modelo puede ejecutarse de forma independiente desde su directorio correspondiente.

### Dashboard de Monitoreo
```bash
# Levantar dashboard Streamlit (6 paginas)
streamlit run dashboard/app.py
```

### Reporte Email
```bash
# Enviar reporte de primera vuelta via Outlook COM
python -m core.email_report --tipo primera_vuelta --fecha 2026-03-13

# Abrir en Outlook para revision (sin enviar)
python -m core.email_report --tipo primera_vuelta --fecha 2026-03-13 --modo display
```


## Configuración

1. Configurar las rutas en `config/config_rutas_ext_y_archivos.yaml`
2. Colocar las credenciales de GCP en la carpeta `credenciales/`
3. Ajustar los parámetros específicos de cada modelo en sus carpetas `parametros/`

## Seguridad

⚠️ **Importante**: Las credenciales y archivos sensibles están excluidos del control de versiones mediante `.gitignore`. Asegúrate de configurar las credenciales localmente antes de ejecutar el sistema.


