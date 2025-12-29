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

Los modelos están diseñados para procesar datos en lotes, generar predicciones y cargar los resultados a BigQuery para su posterior análisis y reporting.

## Estructura del Proyecto

### 📁 Directorio Raíz
```
main.py                          # Punto de entrada principal de la aplicación
VARIACION_CARTERA_ML.xlsm       # Archivo de análisis de variación de cartera
```

### 📁 Configuración y Core
```
config/                          # Configuraciones del sistema
├── config_rutas_ext_y_archivos.yaml  # Rutas externas y archivos de configuración
├── config_rutas.py              # Configuración de rutas del sistema
└── __init__.py

core/                           # Núcleo del sistema
├── orquestador.py              # Orquestador principal de procesos
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
├── ml_mora_cae_cc.xlsm         # Plantilla Excel para cálculos
└── parametros/                 # Parámetros específicos del modelo

RF_Modelo_Mora_Comercial/       # Modelo de mora para créditos comerciales
├── ml_mora_comercial.py        # Implementación del modelo
├── ml_mora_comercial_cc.xlsm   # Plantilla Excel para cálculos
└── parametros/                 # Parámetros específicos del modelo

RF_Modelo_Mora_Consumo/         # Modelo de mora para créditos de consumo
├── ml_mora_consumo.py          # Implementación del modelo
├── ml_mora_consumo_cc.xlsm     # Plantilla Excel para cálculos
├── ml_mora_renegociado_cc.xlsm # Plantilla para créditos renegociados
└── parametros/                 # Parámetros específicos del modelo

RF_Modelo_Mora_Hipotecario/     # Modelo de mora para créditos hipotecarios
├── ml_mora_hipotecario.py      # Implementación del modelo
├── ml_mora_hipotecario_cc.xlsm # Plantilla Excel para cálculos
└── parametros/                 # Parámetros específicos del modelo
```

#### Modelos de Prepago
```
RF_Modelo_Prepago_CMR/          # Modelo de prepago para tarjetas CMR
├── mr_prepago_cmr.py           # Implementación del modelo
├── mr_prepago_cmr.xlsm         # Plantilla Excel para cálculos
├── Generador_Prepago_TC_CMR_Productivo.ipynb  # Notebook de desarrollo
└── parametros/                 # Parámetros específicos del modelo

RF_Modelo_Prepago_Consumo/      # Modelo de prepago para créditos de consumo
├── mr_prepago_consumo.py       # Implementación del modelo
├── mr_prepago_consumo.xlsm     # Plantilla Excel para cálculos
├── EJECUCIONES/                # Historial de ejecuciones
└── parametros/                 # Parámetros específicos del modelo

RF_Modelo_Prepago_Hipotecario/  # Modelo de prepago para créditos hipotecarios
├── mr_prepago_hipotecario.py   # Implementación del modelo
├── mr_prepago_hipotecario.xlsm # Plantilla Excel para cálculos
├── EJECUCIONES/                # Historial de ejecuciones
├── OTROS/                      # Archivos adicionales
└── parametros/                 # Parámetros específicos del modelo
```

### 📁 Documentación
```
docs/                           # Documentación del proyecto
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


### Flujo Principal
1. **Orquestación**: El `orquestador.py` coordina la ejecución de todos los modelos
2. **Modelos**: Cada modelo procesa sus datos específicos y genera predicciones usando `ejecutar_modelo()`
3. **Carga a GCP**: Los resultados se cargan automáticamente a BigQuery
4. **Interfaz**: La GUI permite monitorear y controlar las ejecuciones

### Componentes Clave
- **Orquestador**: Maneja la secuencia de ejecución y dependencias entre modelos
- **Modelos ML**: Implementaciones independientes con interfaz unificada `ejecutar_modelo()`
- **Configuración**: Sistema centralizado de configuración de rutas y parámetros
- **Carga GCP**: Módulos especializados para la integración con Google Cloud Platform

## Requisitos

- Python 3.11+
- Acceso a Google Cloud Platform (BigQuery)
- Credenciales de servicio configuradas
- Librerías especificadas en cada módulo de modelo
- Librería customizada bfa_cl_utilidades: https://gitlab.falabella.tech/rmunozb/bfa-cl-utilidades

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
- `--listar`: Mostrar modelos disponibles y su estado

### Ejecución de Modelos Individuales
Cada modelo puede ejecutarse de forma independiente desde su directorio correspondiente.


## Configuración

1. Configurar las rutas en `config/config_rutas_ext_y_archivos.yaml`
2. Colocar las credenciales de GCP en la carpeta `credenciales/`
3. Ajustar los parámetros específicos de cada modelo en sus carpetas `parametros/`

## Seguridad

⚠️ **Importante**: Las credenciales y archivos sensibles están excluidos del control de versiones mediante `.gitignore`. Asegúrate de configurar las credenciales localmente antes de ejecutar el sistema.


